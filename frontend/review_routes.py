from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from datetime import datetime
import json, secrets

reviews_bp = Blueprint('passenger_reviews', __name__)


def register_review_routes(app, db, base_dir):
    root = base_dir.parent
    routes_file = base_dir / 'all_buses.json'
    model_file = root / 'data' / 'sentiment_model' / 'sentiment_pipeline.joblib'
    keyword_file = root / 'analysis' / 'keywords.json'

    @reviews_bp.post('/api/reviews')
    def submit_review():
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        data = request.get_json(silent=True) or {}
        vehicle_number = str(data.get('vehicle_number', '')).strip()
        review = str(data.get('review', '')).strip()
        rating = data.get('rating')
        if not vehicle_number or not review:
            return jsonify({'error': 'Choose a bus and enter your review.'}), 400
        if len(review) > 5000:
            return jsonify({'error': 'Review must be 5,000 characters or fewer.'}), 400
        try:
            rating = int(rating) if rating not in (None, '') else None
        except (TypeError, ValueError):
            return jsonify({'error': 'Rating must be from 1 to 5.'}), 400
        if rating is not None and rating not in range(1, 6):
            return jsonify({'error': 'Rating must be from 1 to 5.'}), 400
        try:
            with routes_file.open(encoding='utf-8') as f:
                all_buses = json.load(f)
            current = None
            for key, value in all_buses.items():
                number = str(value.get('vehicle_number', key)).strip()
                observations = value.get('observations', [])
                if number == vehicle_number and observations:
                    current = max(observations, key=lambda o: o.get('timestamp', 0))
                    break
            if not current or not current.get('route_id') or not current.get('route_name'):
                return jsonify({'error': 'That bus is not currently listed as operating.'}), 400
            if not model_file.exists():
                return jsonify({'error': 'Sentiment analysis model is not installed.'}), 503
            import joblib
            sentiment = str(joblib.load(model_file).predict([review])[0]).strip().title()
            if sentiment not in {'Positive', 'Negative', 'Neutral'}:
                raise ValueError('Model returned unsupported sentiment')
            with keyword_file.open(encoding='utf-8') as f:
                keywords = json.load(f)
            normalized = ' '.join(review.lower().split())
            scores = {category: sum(word in normalized for word in words)
                      for category, words in keywords.items()}
            category = max(scores, key=scores.get) if scores and max(scores.values()) else 'Other'
            route_id = str(current['route_id']).strip()
            route_name = str(current['route_name']).strip()
            now = datetime.now()
            db.session.execute(text('SELECT pg_advisory_xact_lock(734219861)'))
            review_id = None
            while review_id is None:
                candidate = 1_000_000_000_000 + secrets.randbelow(8_000_000_000_000_000_000)
                if db.session.execute(text('SELECT 1 FROM reviews WHERE review_id=:id'), {'id': candidate}).first() is None:
                    review_id = candidate
            # There is no staff status column. Latest-date assignments define the available roster.
            driver_id = db.session.execute(text('''SELECT driver_id FROM service_assignments
                WHERE driver_id IS NOT NULL AND service_date=(SELECT MAX(service_date) FROM service_assignments)
                ORDER BY random() LIMIT 1''')).scalar_one_or_none()
            conductor_id = db.session.execute(text('''SELECT conductor_id FROM service_assignments
                WHERE conductor_id IS NOT NULL AND service_date=(SELECT MAX(service_date) FROM service_assignments)
                ORDER BY random() LIMIT 1''')).scalar_one_or_none()
            if driver_id is None or conductor_id is None:
                db.session.rollback()
                return jsonify({'error': 'No available driver or conductor roster was found.'}), 503
            db.session.execute(text('INSERT INTO buses(vehicle_number) VALUES (:v) ON CONFLICT DO NOTHING'), {'v': vehicle_number})
            db.session.execute(text('''INSERT INTO routes(route_id,route_name,first_stop,last_stop)
                VALUES (:id,:name,:first,:last) ON CONFLICT (route_id) DO UPDATE SET
                route_name=EXCLUDED.route_name,first_stop=EXCLUDED.first_stop,last_stop=EXCLUDED.last_stop'''),
                {'id': route_id, 'name': route_name, 'first': current.get('first_stop'), 'last': current.get('last_stop')})
            db.session.execute(text('''INSERT INTO bus_route_pairs(vehicle_number,route_id,source_timestamp)
                VALUES (:v,:r,to_timestamp(:ts/1000.0)) ON CONFLICT (vehicle_number,route_id)
                DO UPDATE SET source_timestamp=EXCLUDED.source_timestamp'''),
                {'v': vehicle_number, 'r': route_id, 'ts': current.get('timestamp', 0)})
            assignment_id = db.session.execute(text('''INSERT INTO service_assignments
                (service_date,vehicle_number,route_id,driver_id,conductor_id,assignment_type)
                VALUES (CURRENT_DATE,:v,:r,:d,:c,'live-review')
                ON CONFLICT (service_date,vehicle_number) DO UPDATE SET route_id=EXCLUDED.route_id,
                driver_id=COALESCE(service_assignments.driver_id,EXCLUDED.driver_id),
                conductor_id=COALESCE(service_assignments.conductor_id,EXCLUDED.conductor_id),
                assignment_type=EXCLUDED.assignment_type RETURNING assignment_id'''),
                {'v': vehicle_number, 'r': route_id, 'd': driver_id, 'c': conductor_id}).scalar_one()
            db.session.execute(text('INSERT INTO review_categories(category_name) VALUES (:c) ON CONFLICT DO NOTHING'), {'c': category})
            scenario_id = db.session.execute(text('''INSERT INTO review_scenarios(category_id,scenario_name)
                SELECT category_id,'Passenger submitted review' FROM review_categories WHERE category_name=:c
                ON CONFLICT (category_id,scenario_name) DO UPDATE SET scenario_name=EXCLUDED.scenario_name
                RETURNING scenario_id'''), {'c': category}).scalar_one()
            db.session.execute(text('''INSERT INTO reviews(review_id,assignment_id,scenario_id,review_text,
                rating,sentiment,reviewed_at,time_of_day,source_route_label,source_dataset)
                VALUES (:id,:a,:s,:review,:rating,:sentiment,:now,:time,:route,'passenger_submission')'''),
                {'id': review_id, 'a': assignment_id, 's': scenario_id, 'review': review,
                 'rating': rating, 'sentiment': sentiment, 'now': now,
                 'time': now.strftime('%p').title(), 'route': route_name})
            db.session.commit()
            return jsonify({'message': 'Review submitted successfully.', 'review_id': review_id,
                            'route_name': route_name, 'category': category, 'sentiment': sentiment}), 201
        except Exception:
            db.session.rollback()
            app.logger.exception('Unable to submit review')
            return jsonify({'error': 'Unable to submit review right now.'}), 500

    app.register_blueprint(reviews_bp)