import argparse
import joblib


MODEL_PATH = "sentiment_model/sentiment_pipeline.joblib"


def predict(model, review):
    sentiment = model.predict([review])[0]
    probabilities = model.predict_proba([review])[0]

    print("\nReview:", review)
    print("Predicted Sentiment:", sentiment)

    print("\nPrediction probabilities:")
    for label, probability in zip(model.classes_, probabilities):
        print(f"{label}: {probability:.2%}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", type=str)
    args = parser.parse_args()

    model = joblib.load(MODEL_PATH)

    if args.text:
        predict(model, args.text)
    else:
        while True:
            review = input("\nEnter a passenger review (quit to exit): ").strip()

            if review.lower() == "quit":
                break

            if review:
                predict(model, review)


if __name__ == "__main__":
    main()
