EVAL_DATASET = [
    {
        "question": "When should the patient return to work or school?",
        "expected_answer_contains": [
            "doctor",
            "2 to 3 days",
            "mild and nearly gone"
        ],
        "expected_source_pages": [3, 4]
    },
    {
        "question": "What danger signs are listed?",
        "expected_answer_contains": [
            "headache",
            "vomiting",
            "confusion",
            "drowsiness",
            "slurred speech",
            "seizures",
            "loss of consciousness"
        ],
        "expected_source_pages": [1]
    },
    {
        "question": "What should the patient do in the first few days after injury?",
        "expected_answer_contains": [
            "resting",
            "short time off",
            "symptoms are generally more severe"
        ],
        "expected_source_pages": [3]
    }
]