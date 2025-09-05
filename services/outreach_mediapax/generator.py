def generate_pack(lead: dict) -> dict:
    # Minimal stub: craft titles/copy from vertical + geo
    vertical = lead.get("vertical","")
    state = lead.get("contact",{}).get("state","")
    return {
        "headline": f"{vertical.title()} Growth Pack for {state}",
        "scripts": [
            {"hook":"0-3s", "text":"Stop scrolling—instant shine in 3 hours."},
            {"benefit":"3-9s", "text":"Less hassle, more bookings this week."},
            {"proof":"9-15s", "text":"Before/After splits + local reviews."},
            {"cta":"15-20s", "text":"Tap to book today."}
        ],
        "assets": []
    }