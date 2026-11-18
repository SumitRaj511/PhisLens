from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


_FICTIONAL_TRAINING_EMAILS = [
    ("Urgent account notice: verify your password now or your mailbox will be suspended.", 1),
    ("Your package is delayed. Pay a small redelivery fee today using this shortened link.", 1),
    ("Please buy gift cards immediately and send the redemption codes. Keep this confidential.", 1),
    ("The supplier bank details have changed. Wire the invoice payment to the new account today.", 1),
    ("Your account will be closed unless you enter your password and verification code.", 1),
    ("Open the attached invoice macro document and enable editing to view the payment details.", 1),
    ("Microsoft support needs you to confirm your credentials to restore access to your mailbox.", 1),
    ("A final notice says your payment is overdue. Sign in now to avoid account suspension.", 1),
    ("I am the director. Send the confidential payroll file and do not tell anyone.", 1),
    ("The attached executable contains the updated delivery information. Run it immediately.", 1),
    ("Your one time MFA passcode is required to stop this security alert and unlock your account.", 1),
    ("Use the new bank routing details for this urgent wire transfer. Reply when complete.", 1),
    ("We detected suspicious sign in activity. Verify your identity at this account login page.", 1),
    ("The invoice is overdue. Open the zip attachment and pay the late fee today.", 1),
    ("Your email storage is full. Enter your password to keep your account active.", 1),
    ("Please enable macros in the attached spreadsheet to review the revised payment schedule.", 1),
    ("The CEO requests a confidential wire transfer before close of business. Act now.", 1),
    ("A verification code and password are needed to prevent your profile from being deactivated.", 1),
    ("Parcel tracking requires an immediate fee payment through this tiny URL.", 1),
    ("Please change the beneficiary bank account for the scheduled supplier payment.", 1),
    ("Your account is locked. Sign in and confirm your credentials to restore access.", 1),
    ("The vendor cannot access the portal. Use the attached new payment instructions.", 1),
    ("You have an overdue invoice. Send payment to the updated account and keep it secret.", 1),
    ("Click the secure login link now to validate your password and MFA token.", 1),
    ("Your library book is ready for collection during the regular opening hours.", 0),
    ("The team meeting is scheduled for Thursday at 10. The agenda is attached for review.", 0),
    ("Thanks for sending the project notes. I will review them before our next meeting.", 0),
    ("Your order has shipped. You can view the receipt in the store app you already use.", 0),
    ("The office will be closed on Monday for the public holiday. Normal hours resume Tuesday.", 0),
    ("Attached is the quarterly report for the regular department review.", 0),
    ("Please let me know whether you are available for lunch after the conference.", 0),
    ("The requested book is ready at the main library desk. See the opening hours page.", 0),
    ("The meeting room reservation is confirmed for 2 pm. Reply if you need to change it.", 0),
    ("Your monthly statement is available in the banking application. No action is required.", 0),
    ("Here are the minutes from yesterday. The next planning call is on the shared calendar.", 0),
    ("Thank you for your application. We will contact you after the review is complete.", 0),
    ("The supplier invoice matches the purchase order already approved by finance.", 0),
    ("I have updated the presentation. Please add comments before our scheduled review.", 0),
    ("Your appointment is confirmed for Friday. Call the clinic using its usual phone number.", 0),
    ("The new staff handbook is on the company intranet. Contact HR if you have questions.", 0),
    ("The parcel was delivered to reception. Please collect it during normal business hours.", 0),
    ("The training course starts next week. The calendar invitation has the joining details.", 0),
    ("I received your message and will follow up through our usual project channel.", 0),
    ("The weekly report is ready. I saved it in the team folder for review.", 0),
    ("Your subscription renewal receipt is in the account page you normally use.", 0),
    ("The updated schedule is attached. Please confirm which time works best for the team.", 0),
    ("We received the signed form. No further action is needed at this time.", 0),
]

_MODEL = Pipeline([
    ("tfidf", TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        max_features=4000,
        sublinear_tf=True,
        stop_words="english",
    )),
    ("classifier", LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=7,
    )),
])
_MODEL.fit(
    [email for email, _label in _FICTIONAL_TRAINING_EMAILS],
    [label for _email, label in _FICTIONAL_TRAINING_EMAILS],
)


def preview_model(text: str) -> dict[str, Any]:
    if len(text.split()) < 4:
        return {
            "available": False,
            "message": "More text is needed for the experimental model preview.",
            "score": None,
            "tendency": None,
            "terms": [],
        }

    vectorizer = _MODEL.named_steps["tfidf"]
    classifier = _MODEL.named_steps["classifier"]
    matrix = vectorizer.transform([text])
    if matrix.nnz == 0:
        return {
            "available": False,
            "message": "The experimental model found no familiar terms in this text.",
            "score": None,
            "tendency": None,
            "terms": [],
        }

    probability = float(_MODEL.predict_proba([text])[0][1])
    contributions = matrix.multiply(classifier.coef_[0]).toarray()[0]
    feature_names = vectorizer.get_feature_names_out()
    positive = sorted(
        (
            (float(contribution), str(feature_names[index]))
            for index, contribution in enumerate(contributions)
            if contribution > 0
        ),
        reverse=True,
    )[:3]
    terms = [term for _contribution, term in positive]
    return {
        "available": True,
        "message": "Experimental only — trained on fictional examples, not validated on real email.",
        "score": round(probability * 100),
        "tendency": "More phishing-like terms" if probability >= 0.5 else "Fewer phishing-like terms",
        "terms": terms,
    }
