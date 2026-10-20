import markdown

md = markdown.Markdown(
    extensions=["fenced_code", "tables", "codehilite", "toc"],
    extension_configs={
        "codehilite": {
            "css_class": "highlight",
            "guess_lang": False,
        }
    },
)
