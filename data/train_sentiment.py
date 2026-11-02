import argparse
from pathlib import Path

import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    # Only review and sentiment are used for training.
    df = df[["review", "sentiment"]].dropna().copy()

    df["review"] = df["review"].astype(str).str.strip()
    df["sentiment"] = df["sentiment"].astype(str).str.strip().str.title()

    df = df[
        (df["review"] != "") &
        (df["sentiment"] != "")
    ]

    # Remove exact duplicate reviews and conflicting labels.
    df["normalized"] = (
        df["review"]
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    conflicts = df.groupby("normalized")["sentiment"].nunique()
    conflicts = conflicts[conflicts > 1].index
    df = df[~df["normalized"].isin(conflicts)]
    df = df.drop_duplicates(subset="normalized")

    print("Total usable reviews:", len(df))
    print("\nSentiment distribution:")
    print(df["sentiment"].value_counts())

    X = df["review"]
    y = df["sentiment"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            max_features=20000,
            min_df=2,
            sublinear_tf=True
        )),
        ("classifier", LogisticRegression(
            max_iter=2000,
            class_weight="balanced"
        ))
    ])

    print("\nTraining sentiment analysis model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("\nAccuracy:", accuracy_score(y_test, predictions))
    print("\nClassification Report:")
    print(classification_report(y_test, predictions, zero_division=0))

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions, labels=model.classes_))
    print("Label order:", model.classes_)

    Path("sentiment_model").mkdir(exist_ok=True)

    joblib.dump(
        model,
        "sentiment_model/sentiment_pipeline.joblib"
    )

    print("\nModel saved successfully!")


if __name__ == "__main__":
    main()
