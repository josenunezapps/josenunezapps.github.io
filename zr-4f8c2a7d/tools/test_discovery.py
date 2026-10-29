import unittest
from enrich import commercial_record, prepare_snapshot

TODAY = "2026-10-28"


def osm(name="Farmacia Ejemplo", osm_id=15, **tags):
    return {"type": "node", "id": osm_id, "lat": -54.81, "lon": -68.31,
            "tags": {"name": name, "shop": "chemist", **tags}}


class OSMDiscoveryTests(unittest.TestCase):
    def test_snapshot_keeps_valid_business_and_source(self):
        s = prepare_snapshot([osm()], {}, 1, 4, TODAY)
        self.assertEqual(len(s["records"]), 1)
        self.assertEqual(s["records"][0]["id"], "node/15")
        self.assertEqual(s["records"][0]["lastObserved"], TODAY)
        self.assertEqual(s["status"], "partial")

    def test_ignores_unnamed_and_uncommercial_and_invalid_place(self):
        objects = [
            osm(name=""),
            {"type": "node", "id": 20, "lat": -54.80, "lon": -68.32, "tags": {"name": "Casa particular"}},
            {"type": "node", "id": 21, "lat": -30, "lon": -68.32, "tags": {"name": "Lejos", "shop": "bakery"}},
            osm(name="Local legítimo", osm_id=22),
        ]
        result = prepare_snapshot(objects, {}, 1, 4, TODAY)
        self.assertEqual([r["id"] for r in result["records"]], ["node/22"])

    def test_preserves_old_snapshot_on_total_failure(self):
        old = prepare_snapshot([osm()], {}, 1, 4, "2026-10-27")
        new = prepare_snapshot([], old, 0, 4, TODAY)
        self.assertEqual(new["records"], old["records"])
        self.assertEqual(new["generatedAt"], "2026-10-27")
        self.assertEqual(new["status"], "unavailable")

    def test_partial_updates_and_keeps_prior_records(self):
        before = prepare_snapshot([osm(osm_id=15)], {}, 1, 4, "2026-10-27")
        after = prepare_snapshot([osm(name="Panadería Segunda", osm_id=16, shop="bakery")], before, 1, 4, TODAY)
        self.assertEqual({r["id"] for r in after["records"]}, {"node/15", "node/16"})
        self.assertEqual(next(r for r in after["records"] if r["id"] == "node/15")["lastObserved"], "2026-10-27")

    def test_only_strict_website_and_instagram(self):
        obj = commercial_record(osm(website="javascript:alert(1)",
                                    **{"contact:instagram": "https://instagram.com/cafe_ejemplo"}), TODAY)
        self.assertEqual(obj["website"], "")
        self.assertEqual(obj["instagram"], "cafe_ejemplo")

    def test_category_is_compatible_with_radar(self):
        obj = commercial_record(osm(name="Restaurante Ejemplo", amenity="restaurant", shop="restaurant"), TODAY)
        self.assertEqual(obj["category"], "Gastronomía")

    def test_duplicate_id_is_not_duplicated(self):
        s = prepare_snapshot([osm(), osm()], {}, 1, 4, TODAY)
        self.assertEqual(len(s["records"]), 1)


if __name__ == "__main__":
    unittest.main()
