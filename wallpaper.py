"""Daily DSA revision wallpaper.

Shows a problem you already solved: description/approach on the left,
your complete submitted solution (from GitHub) on the right.
Run manually or via Task Scheduler (see README.md).
"""

import ctypes
import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "today.png"
FONTS = Path(r"C:\Windows\Fonts")

START = date(2026, 7, 14)  # day 000
TRACKER = HERE.parent / "whooppp" / "dsa" / "problems.json"
GITHUB_REPO = "chiragduhoon/leetcode-solutions"

TEXT = (237, 242, 248)
MUTED = (148, 158, 172)
FAINT = (82, 90, 104)
CODE = (190, 214, 255)
PANEL = (16, 21, 32)
PANEL_EDGE = (44, 52, 68)

DIFFICULTY_COLORS = {
    "Easy": (63, 185, 80),
    "Medium": (255, 166, 87),
    "Hard": (248, 81, 73),
}


def screen_size():
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def load_font(name, size):
    try:
        return ImageFont.truetype(str(FONTS / name), size)
    except OSError:
        return ImageFont.load_default(size)


def wrap(draw, text, font, max_width):
    lines = []
    for para in text.split("\n"):
        words = para.split()
        cur = ""
        for word in words:
            trial = f"{cur} {word}".strip()
            if draw.textlength(trial, font=font) <= max_width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def wrap_mono(draw, line, font, max_width):
    """Character-wrap a monospace line that exceeds max_width."""
    out = []
    while draw.textlength(line, font=font) > max_width and len(line) > 1:
        cut = len(line)
        while cut > 1 and draw.textlength(line[:cut], font=font) > max_width:
            cut -= 1
        out.append(line[:cut])
        line = "  " + line[cut:]
    out.append(line)
    return out


def normalize(s):
    """Lowercase alphanumerics only — matches slugs against problem names."""
    return "".join(c for c in s.lower() if c.isalnum())


def refresh_solved():
    """Refresh solved.json from the GitHub repo; keep the old copy on failure."""
    import urllib.request
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/main?recursive=1"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            tree = json.load(r).get("tree", [])
        slugs = sorted({t["path"].split("/")[0] for t in tree if "/" in t["path"]})
        if slugs:
            (HERE / "solved.json").write_text(
                json.dumps({"repo": GITHUB_REPO, "slugs": slugs}, indent=1),
                encoding="utf-8")
    except Exception:
        pass  # offline / rate-limited: use the cached file


def load_solutions():
    """Merge every solutions*.json into one name -> card dict."""
    merged = {}
    for f in sorted(HERE.glob("solutions*.json")):
        merged.update(json.loads(f.read_text(encoding="utf-8")))
    return merged


def fetch_solution(slug):
    """Get the complete submitted solution file for a problem from GitHub.

    Cached locally in cache/ so each problem is downloaded once.
    """
    import urllib.request
    cache = HERE / "cache"
    cache.mkdir(exist_ok=True)
    cached = cache / f"{slug}.txt"
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    for ext in ("cpp", "py", "sql"):
        url = (f"https://raw.githubusercontent.com/{GITHUB_REPO}"
               f"/main/{slug}/solution.{ext}")
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                code = r.read().decode("utf-8")
            cached.write_text(code, encoding="utf-8")
            return code
        except Exception:
            continue
    return None


def clean_code(code):
    """Keep the code as written — just expand tabs and trim edges."""
    lines = [l.expandtabs(4).rstrip() for l in code.strip().splitlines()]
    return "\n".join(lines)


def fetch_example(slug, max_lines=10):
    """Pull Example 1 (Input/Output) from the problem's README on GitHub."""
    import re
    import urllib.request
    cache = HERE / "cache"
    cache.mkdir(exist_ok=True)
    cached = cache / f"{slug}.md"
    if cached.exists():
        md = cached.read_text(encoding="utf-8")
    else:
        url = (f"https://raw.githubusercontent.com/{GITHUB_REPO}"
               f"/main/{slug}/README.md")
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                md = r.read().decode("utf-8")
            cached.write_text(md, encoding="utf-8")
        except Exception:
            return None
    m = re.search(r"Example 1:.*?```(.*?)```", md, re.S)
    if not m:
        return None
    lines = [l.strip().replace("**", "") for l in m.group(1).splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        return None
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + ["..."]
    return "\n".join(lines)


def pick_revision():
    """Pick a solved problem to revise.

    Solved list comes from the GitHub repo (solved.json); approach cards
    from solutions*.json; difficulty/dates enriched from the whooppp
    tracker when the problem is logged there.
    """
    refresh_solved()
    solved = json.loads((HERE / "solved.json").read_text(encoding="utf-8"))
    solutions = load_solutions()

    by_key = {normalize(name): (name, card) for name, card in solutions.items()}
    tracker = {}
    if TRACKER.exists():
        for p in json.loads(TRACKER.read_text(encoding="utf-8")):
            if p.get("status") == "solved":
                tracker[normalize(p["name"])] = p

    pool = []
    for slug in solved["slugs"]:
        key = normalize(slug.split("-", 1)[1] if "-" in slug else slug)
        if key in by_key:
            name, card = by_key[key]
            pool.append((name, card, tracker.get(key, {}), slug))
    if not pool:
        return None

    today = date.today().isoformat()

    def is_due(meta):
        return not meta.get("next_revision_date") or meta["next_revision_date"] <= today

    due = [x for x in pool if is_due(x[2])]
    rotation = due if due else pool
    rotation.sort(key=lambda x: (x[2].get("next_revision_date") or "",
                                 x[2].get("date_solved") or "", x[0]))

    day = (date.today() - START).days
    name, sol, meta, slug = rotation[day % len(rotation)]

    # your complete submitted solution, exactly as written
    full = fetch_solution(slug)
    code = clean_code(full) if full else sol.get("code")

    difficulty = meta.get("difficulty") or sol.get("difficulty", "?")
    topic = meta.get("subtopic") or meta.get("topic") or sol.get("topic", "DSA")
    card = {
        "category": f"{difficulty}  ·  {topic}",
        "title": name,
        "signal": sol.get("signal"),
        "body": sol["approach"],
        "example": fetch_example(slug),
        "code": code,
        "complexity": sol.get("complexity"),
    }
    accent = DIFFICULTY_COLORS.get(difficulty, (88, 166, 255))
    solved_on = f"solved {meta['date_solved']}" if meta.get("date_solved") else "from github"
    footer = f"REVISE  ·  {solved_on}  ·  {len(due)} due of {len(pool)}"
    idx = sorted(x[0] for x in pool).index(name)
    return card, idx, len(pool), footer, accent


def make_background(width, height, accent):
    """Vertical gradient, category-tinted glow, and a faint dot grid."""
    top = (10, 13, 22)
    bottom = (16, 18, 34)
    strip = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        strip.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    bg = strip.resize((width, height))

    glow = Image.new("RGB", (width, height), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = int(height * 0.55)
    gd.ellipse(
        [int(width * 0.30) - r, int(height * 0.25) - r,
         int(width * 0.30) + r, int(height * 0.25) + r],
        fill=tuple(int(c * 0.16) for c in accent),
    )
    r2 = int(height * 0.45)
    gd.ellipse(
        [int(width * 0.85) - r2, int(height * 0.95) - r2,
         int(width * 0.85) + r2, int(height * 0.95) + r2],
        fill=tuple(int(c * 0.10) for c in accent),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(int(height * 0.12)))
    bg = ImageChops.add(bg, glow)

    dots = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    step = max(36, int(height * 0.036))
    for y in range(step, height, step):
        for x in range(step, width, step):
            dd.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, 10))
    return Image.alpha_composite(bg.convert("RGBA"), dots)


def pill(draw, xy, text, font, fg, outline, fill=None, pad_x=18, pad_y=9):
    x, y = xy
    w = draw.textlength(text, font=font)
    asc, desc = font.getmetrics()
    h = asc + desc
    box = [x, y, x + w + 2 * pad_x, y + h + 2 * pad_y]
    draw.rounded_rectangle(box, radius=(h + 2 * pad_y) // 2, fill=fill, outline=outline, width=2)
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg)
    return box[2]


def render(fact, index, total, width, height, accent=None, footer_label=None):
    scale = height / 1080
    if accent is None:
        accent = (88, 166, 255)
    accent_dim = tuple(int(c * 0.55) for c in accent)

    img = make_background(width, height, accent)
    draw = ImageDraw.Draw(img)

    f_pill = load_font("segoeuib.ttf", int(19 * scale))
    f_title = load_font("segoeuib.ttf", int(46 * scale))
    f_signal_label = load_font("segoeuib.ttf", int(18 * scale))
    f_signal = load_font("segoeuii.ttf", int(22 * scale))
    f_body = load_font("segoeui.ttf", int(26 * scale))
    f_footer = load_font("segoeui.ttf", int(19 * scale))
    f_big = load_font("segoeuib.ttf", int(280 * scale))

    code_lines = fact.get("code", "").split("\n") if fact.get("code") else []
    line_gap = int(11 * scale)

    if code_lines:
        # two columns: description left, complete solution right
        margin_x = int(width * 0.185)
        text_width = int(width * 0.345)
        code_x0 = int(width * 0.575)
        code_x1 = int(width * 0.965)
    else:
        margin_x = int(width * 0.34)
        text_width = int(width * 0.46)
        code_x0 = code_x1 = 0

    # giant faint day number, bottom-left behind the text column
    big = f"{index:03d}"
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.text((int(width * 0.04), height - int(400 * scale)),
            big, font=f_big, fill=accent + (12,))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # ---- left column: pills, title, signal, body ----
    title_lines = wrap(draw, fact["title"], f_title, text_width)
    signal_lines = (
        wrap(draw, fact["signal"], f_signal, text_width - int(30 * scale))
        if fact.get("signal") else []
    )
    body_lines = wrap(draw, fact["body"], f_body, text_width)

    pill_h = sum(f_pill.getmetrics()) + int(18 * scale) + int(36 * scale)
    title_h = sum(f_title.getbbox(l)[3] + line_gap for l in title_lines)
    signal_h = (
        sum(f_signal.getbbox(l)[3] + line_gap for l in signal_lines)
        + sum(f_signal_label.getmetrics()) + int(30 * scale)
    ) if signal_lines else 0
    body_h = sum(f_body.getbbox(l)[3] + line_gap for l in body_lines)

    f_ex = load_font("consola.ttf", int(19 * scale))
    f_ex_label = load_font("segoeuib.ttf", int(18 * scale))
    ex_lines = []
    if fact.get("example"):
        for raw in fact["example"].split("\n"):
            ex_lines += wrap_mono(draw, raw, f_ex, text_width - int(40 * scale))
    ex_line_h = f_ex.getbbox("Ay")[3] + int(7 * scale)
    ex_pad = int(18 * scale)
    ex_h = (sum(f_ex_label.getmetrics()) + int(10 * scale)
            + len(ex_lines) * ex_line_h + 2 * ex_pad + int(28 * scale)) if ex_lines else 0

    block_h = pill_h + title_h + signal_h + int(26 * scale) + body_h + ex_h

    y = max(int(height * 0.08), (height - block_h) // 2)

    x_end = pill(draw, (margin_x, y), fact["category"].upper(), f_pill,
                 fg=accent, outline=accent_dim,
                 pad_x=int(18 * scale), pad_y=int(9 * scale))
    if fact.get("complexity"):
        cx = x_end + int(14 * scale)
        cw = draw.textlength(fact["complexity"], font=f_pill) + int(36 * scale)
        if cx + cw > margin_x + text_width + int(40 * scale):
            cx = margin_x                      # wrap the pill to its own row
            y += sum(f_pill.getmetrics()) + int(28 * scale)
            block_h += sum(f_pill.getmetrics()) + int(28 * scale)
        pill(draw, (cx, y), fact["complexity"], f_pill,
             fg=MUTED, outline=(58, 66, 82),
             pad_x=int(18 * scale), pad_y=int(9 * scale))
    y += pill_h

    for line in title_lines:
        draw.text((margin_x, y), line, font=f_title, fill=TEXT)
        y += f_title.getbbox(line)[3] + line_gap
    y += int(26 * scale)

    if signal_lines:
        draw.text((margin_x, y), "WHEN YOU SEE", font=f_signal_label, fill=accent)
        y += sum(f_signal_label.getmetrics()) + int(8 * scale)
        sig_x = margin_x + int(30 * scale)
        bar_top = y + int(4 * scale)
        for line in signal_lines:
            draw.text((sig_x, y), line, font=f_signal, fill=(172, 182, 198))
            y += f_signal.getbbox(line)[3] + line_gap
        draw.rounded_rectangle(
            [margin_x + int(6 * scale), bar_top,
             margin_x + int(10 * scale), y - int(6 * scale)],
            radius=int(2 * scale), fill=accent_dim,
        )
        y += int(22 * scale)

    for line in body_lines:
        draw.text((margin_x, y), line, font=f_body, fill=MUTED)
        y += f_body.getbbox(line)[3] + line_gap

    if ex_lines:
        y += int(28 * scale)
        draw.text((margin_x, y), "EXAMPLE", font=f_ex_label, fill=accent)
        y += sum(f_ex_label.getmetrics()) + int(10 * scale)
        box_h = len(ex_lines) * ex_line_h + 2 * ex_pad
        draw.rounded_rectangle(
            [margin_x, y, margin_x + text_width, y + box_h],
            radius=int(10 * scale), fill=PANEL, outline=PANEL_EDGE, width=2,
        )
        ey = y + ex_pad
        for line in ex_lines:
            color = (172, 182, 198) if line.startswith(("Input", "Output", "Explanation")) else MUTED
            draw.text((margin_x + int(20 * scale), ey), line, font=f_ex, fill=color)
            ey += ex_line_h
        y += box_h

    # ---- right column: the complete solution ----
    if code_lines:
        code_pad = int(24 * scale)
        code_head = int(38 * scale)
        avail_w = code_x1 - code_x0 - 2 * code_pad
        max_code_h = int(height * 0.86)

        size = int(21 * scale)
        while size > 11:
            f_code = load_font("consola.ttf", size)
            lh = f_code.getbbox("Ay")[3] + max(3, int(size * 0.32))
            widest = max(draw.textlength(l, font=f_code) for l in code_lines)
            if (code_head + len(code_lines) * lh + 2 * code_pad <= max_code_h
                    and widest <= avail_w):
                break
            size -= 1
        f_code = load_font("consola.ttf", size)
        code_line_h = f_code.getbbox("Ay")[3] + max(3, int(size * 0.32))
        fit = (max_code_h - code_head - 2 * code_pad) // code_line_h
        if len(code_lines) > fit:                      # extreme cases only
            code_lines = code_lines[:max(3, fit - 1)] + ["// ..."]
        code_h = code_head + len(code_lines) * code_line_h + 2 * code_pad

        cy0 = max(int(height * 0.06), (height - code_h) // 2)
        draw.rounded_rectangle(
            [code_x0, cy0, code_x1, cy0 + code_h],
            radius=int(14 * scale), fill=PANEL, outline=PANEL_EDGE, width=2,
        )
        for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            dot_x = code_x0 + code_pad + i * int(26 * scale)
            dot_y = cy0 + code_head // 2 + int(6 * scale)
            r = int(6 * scale)
            draw.ellipse([dot_x - r, dot_y - r, dot_x + r, dot_y + r], fill=col)
        label = "solution.cpp"
        draw.text((code_x1 - code_pad - draw.textlength(label, font=f_footer),
                   cy0 + code_head // 2 - int(2 * scale)),
                  label, font=f_footer, fill=FAINT)
        ty = cy0 + code_head + code_pad - int(6 * scale)
        for line in code_lines:
            draw.text((code_x0 + code_pad, ty), line, font=f_code, fill=CODE)
            ty += code_line_h

    # ---- footer ----
    fy = height - int(64 * scale)
    label = footer_label or f"DSA DAILY  ·  DAY {index:03d} / {total}"
    draw.text((margin_x, fy), label, font=f_footer, fill=FAINT)
    label_w = draw.textlength(label, font=f_footer)

    bar_x = margin_x + label_w + int(28 * scale)
    bar_w = int(width * 0.14)
    bar_y = fy + int(10 * scale)
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + int(6 * scale)],
                           radius=int(3 * scale), fill=(40, 46, 60))
    done_w = max(int(6 * scale), int(bar_w * (index + 1) / total))
    draw.rounded_rectangle([bar_x, bar_y, bar_x + done_w, bar_y + int(6 * scale)],
                           radius=int(3 * scale), fill=accent)

    date_str = date.today().strftime("%d %b %Y").upper()
    date_w = draw.textlength(date_str, font=f_footer)
    draw.text((width - int(width * 0.035) - date_w, fy), date_str,
              font=f_footer, fill=FAINT)

    return img.convert("RGB")


def set_wallpaper(path):
    SPI_SETDESKWALLPAPER = 20
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    ok = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER, 0, str(path), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    if not ok:
        raise ctypes.WinError()


def main():
    width, height = screen_size()
    picked = pick_revision()
    if not picked:
        print("No revision card available; keeping current wallpaper.")
        return 1
    fact, index, total, footer, accent = picked
    img = render(fact, index, total, width, height,
                 accent=accent, footer_label=footer)
    img.save(OUTPUT)
    set_wallpaper(OUTPUT)
    print(f"Set wallpaper: [{fact['category']}] {fact['title']} ({index}/{total})")


if __name__ == "__main__":
    sys.exit(main())
