from app.ocr import split_recipe_lines


def test_split_with_section_headers():
    text = """Banana Bread
Ingredients:
1 cup butter
2 cups sugar
Directions:
1. Cream the butter and sugar.
2. Bake at 350F.
"""
    result = split_recipe_lines(text)
    assert result["title"] == "Banana Bread"
    assert "1 cup butter" in result["ingredients"]
    assert any("Cream the butter" in s for s in result["steps"])


def test_split_heuristic_without_headers():
    text = """Cookies
2 cups flour
1 tsp salt
Mix until combined.
Bake for 12 minutes.
"""
    result = split_recipe_lines(text)
    assert result["title"] == "Cookies"
    assert any("flour" in i for i in result["ingredients"])
    assert any("Mix" in s or "Bake" in s for s in result["steps"])
