import unittest

from sistema_phishing.training_protocol import (
    TrainingExample,
    clean_training_examples,
    split_fingerprint,
    stratified_split,
    training_text_hash,
)


class TrainingProtocolTests(unittest.TestCase):
    def test_cleaning_removes_duplicates_conflicts_and_holdout_overlap(self):
        examples = [
            TrainingExample("Mensaje repetido", 1, "a"),
            TrainingExample("  mensaje   REPETIDO ", 1, "b"),
            TrainingExample("Contradicción", 0, "a"),
            TrainingExample("contradicción", 1, "b"),
            TrainingExample("Reservado", 0, "a"),
            TrainingExample("Único", 0, "a"),
        ]
        clean, summary = clean_training_examples(
            examples,
            excluded_hashes={training_text_hash("reservado")},
        )
        self.assertEqual(
            [item.text for item in clean], ["Mensaje repetido", "Único"]
        )
        self.assertEqual(summary.removed_duplicate_rows, 1)
        self.assertEqual(summary.removed_conflicting_rows, 2)
        self.assertEqual(summary.conflicting_groups, 1)
        self.assertEqual(summary.removed_overlap_rows, 1)

    def test_stratified_split_is_stable_and_disjoint(self):
        examples = [
            TrainingExample(f"texto {label}-{index}", label, "source")
            for label in (0, 1)
            for index in range(20)
        ]
        train_a, test_a = stratified_split(examples, random_state=42)
        train_b, test_b = stratified_split(examples, random_state=42)
        self.assertEqual(split_fingerprint(train_a), split_fingerprint(train_b))
        self.assertEqual(split_fingerprint(test_a), split_fingerprint(test_b))
        self.assertEqual(len(train_a), 32)
        self.assertEqual(len(test_a), 8)
        self.assertEqual(sum(item.label for item in test_a), 4)
        self.assertTrue(
            {item.text for item in train_a}.isdisjoint(
                item.text for item in test_a
            )
        )


if __name__ == "__main__":
    unittest.main()
