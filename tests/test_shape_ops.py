"""Shape ops: gradient, grid, card, badge, wave, pill render deterministically."""

import unittest

from kit import render
from kit.brand import Brand


def _geo(w=1080, h=1080):
    return {"w": w, "h": h, "scale": min(w, h), "m": round(min(w, h) * 0.06),
            "top": round(h * 0.06), "bottom": round(h * 0.94),
            "wide": w > h, "tight": False}


def _brand():
    return Brand({"palette": {"dark": "#0A1A33", "primary": "#1E5AA8",
                              "accent": "#FF9E00", "white": "#FFFFFF"}, "type": {}}, ".")


SPEC = {
    "id": "shapes",
    "variants": {"portrait": {"layers": [
        {"op": "gradient", "from": "dark", "to": "primary", "angle": 110},
        {"op": "grid", "spacing": "round(scale*0.05)", "opacity": 0.1, "diagonal": True},
        {"op": "wave", "height": "round(h*0.14)", "amplitude": "round(h*0.03)", "color": "white"},
        {"op": "card", "at": ["m", "round(h*0.5)"], "size": ["round(w*0.5)", "round(h*0.1)"],
         "items": [{"label": "Theory", "icon": "check"}, {"label": "Lab", "icon": "ring"},
                   {"label": "Real care", "icon": "dot"}]},
        {"op": "badge", "at": ["round(w*0.7)", "round(h*0.55)"], "size": "round(scale*0.2)",
         "text": "28 weeks\n770 hours"},
        {"op": "pill", "at": ["m", "round(h*0.86)"], "ref": "cta", "color": "accent"},
        {"op": "text", "ref": "copy.hook", "at": ["m", "round(h*0.4)"], "width": "w*0.6",
         "size": "round(scale*0.08)", "color": "white", "accent": "accent"},
    ]}},
}


class ShapeOps(unittest.TestCase):
    def test_renders_and_records_elements(self):
        trace = {}
        img = render.render(SPEC, _brand(), _geo(), copy={"hook": "Are you called to [care?]"},
                            extra={"cta": "Get program info"}, trace=trace)
        self.assertEqual(img.size, (1080, 1080))
        self.assertEqual(img.mode, "RGB")
        ops = {e["op"] for e in trace["elements"]}
        self.assertTrue({"card", "badge", "pill", "text"} <= ops)

    def test_gradient_corners_differ(self):
        spec = {"id": "g", "layers": [{"op": "gradient", "from": "dark", "to": "primary", "angle": 90}]}
        img = render.render(spec, _brand(), _geo())
        top = img.getpixel((540, 5))
        bottom = img.getpixel((540, 1075))
        self.assertNotEqual(top, bottom)
        self.assertLess(sum(top), sum(bottom))  # dark top -> lighter primary bottom

    def test_grid_and_wave_are_background_ops(self):
        self.assertTrue({"gradient", "grid", "wave"} <= render.BG_OPS)
        self.assertTrue({"card", "badge", "pill"} <= set(render.OPS))

    def test_transparent_overlay_skips_background_shapes(self):
        trace = {}
        img = render.render(SPEC, _brand(), _geo(), copy={"hook": "Hi"},
                            extra={"cta": "Go"}, trace=trace, transparent=True)
        self.assertEqual(img.mode, "RGBA")
        ops = {e["op"] for e in trace["elements"]}
        self.assertIn("pill", ops)
        self.assertIn("card", ops)  # foreground panel still drawn over transparency
        # corner stays transparent: gradient/grid/wave are background ops, skipped in overlay
        self.assertEqual(img.getpixel((2, 2))[3], 0)


if __name__ == "__main__":
    unittest.main()