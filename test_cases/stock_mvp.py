
"""
Stock Galton MVP
----------------
A tiny "compressed-time stock market" game powered by a Galton-spinner RNG.

Flow:
1) Pre-round: consult 3 characters (Analyst / Girlfriend / Dentist) for biased hints.
2) Round: price chart moves in real-time (20–30s). You can go LONG or FLAT and choose bet size.
3) End: chart stops, P&L is settled into your balance.

Controls
- [SPACE] start round from consult screen
- [1][2][3] consult Analyst / Girlfriend / Dentist
- [B] buy (go long)   | [S] sell (go flat)
- [UP]/[DOWN] change bet size
- [R] next round from results
- [ESC] quit

No external assets required: the game draws cartoon portraits and saves them as PNGs next to this file.
"""

import os
import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

import pygame as pg


# -----------------------------
# Config
# -----------------------------
W, H = 1200, 720
FPS = 60

ROUND_SECONDS_DEFAULT = 25
STEP_HZ = 12                         # price updates per second (chart smoothness)
DT = 1.0 / STEP_HZ

GALTON_ROWS = 18                     # more rows = closer to normal
START_PRICE = 100.0

BALANCE_START = 1_000_000.0
BET_MIN = 10_000.0
BET_MAX = 500_000.0
BET_STEP = 10_000.0

# price dynamics (hidden "true" params per round)
MU_RANGE = (-0.10, 0.12)             # annualized drift-ish (compressed)
SIGMA_RANGE = (0.18, 0.60)           # annualized vol-ish (compressed)

# visual
CHART_PAD = 18
CHART_BG = (245, 248, 252)
INK = (25, 25, 30)
MUTED = (90, 95, 105)
GREEN = (30, 160, 90)
RED = (200, 60, 60)
BLUE = (55, 120, 220)
YELLOW = (235, 205, 70)
PANEL = (255, 255, 255)
OUTLINE = (15, 15, 20)


# -----------------------------
# Utility drawing
# -----------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def rr(surf, rect, color, r=16):
    pg.draw.rect(surf, color, rect, border_radius=r)

def rro(surf, rect, fill, outline=OUTLINE, r=16, w=4):
    pg.draw.rect(surf, outline, rect.inflate(w, w), border_radius=r + w//2)
    pg.draw.rect(surf, fill, rect, border_radius=r)

def draw_text(surf, text, pos, font, color=INK):
    img = font.render(text, True, color)
    surf.blit(img, pos)
    return img.get_rect(topleft=pos)

def draw_text_center(surf, text, center, font, color=INK):
    img = font.render(text, True, color)
    rect = img.get_rect(center=center)
    surf.blit(img, rect.topleft)
    return rect

def fmt_money(x: float) -> str:
    s = f"{x:,.0f}".replace(",", "'")
    return f"${s}"

def fmt_pct(x: float) -> str:
    return f"{x*100:+.1f}%"

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


# -----------------------------
# Galton RNG -> approx Normal
# -----------------------------
class GaltonSpinner:
    """
    Sample a quasi-normal variable using a Galton board:
    K ~ Binomial(rows, 0.5)  => z ~ (K - rows/2) / sqrt(rows/4)
    """
    def __init__(self, rows: int = GALTON_ROWS):
        self.rows = rows
        self.mean = rows / 2.0
        self.std = math.sqrt(rows * 0.25)

    def sample_z(self) -> float:
        k = 0
        # faster than random.choice([-1,1]) loops; Binomial via Bernoulli sum
        for _ in range(self.rows):
            k += 1 if random.random() < 0.5 else 0
        return (k - self.mean) / self.std

    def sample_return(self, mu: float, sigma: float, dt: float) -> float:
        """
        Geometric-return increment for one time step:
        dS/S ≈ mu*dt + sigma*sqrt(dt)*z
        """
        z = self.sample_z()
        return mu * dt + sigma * math.sqrt(dt) * z


# -----------------------------
# Characters (signals)
# -----------------------------
@dataclass
class Character:
    key: str
    name: str
    title: str
    bias: float                 # systematic tilt to perceived drift
    noise: float                # message noise
    style: str                  # used to draw portrait variant

    def speak(self, true_mu: float, true_sigma: float) -> str:
        """
        Turn hidden params into a short hint string.
        """
        # perceive "direction" with bias + noise
        perceived = true_mu + self.bias + random.gauss(0, self.noise)

        arrow = "📈" if perceived >= 0 else "📉"
        confidence = clamp(1.0 - abs(random.gauss(0, self.noise * 2.2)), 0.15, 0.95)

        # a bit of vol commentary
        vol_tag = "calm" if true_sigma < 0.28 else ("spicy" if true_sigma < 0.45 else "wild")

        lines = [
            f"{arrow}  {self.name} says:",
            f"\"I feel it's {('up' if perceived >= 0 else 'down')}... like {vol_tag} today.\"",
            f"Confidence: {confidence:.0%}",
        ]
        return "\n".join(lines)


# -----------------------------
# Simple portrait generator (cartoon, 90s-ish)
# -----------------------------
def draw_portrait(style: str, size: int = 220) -> pg.Surface:
    """
    Returns a Surface with a simple cartoon portrait.
    """
    surf = pg.Surface((size, size), pg.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # background
    bg = {
        "analyst": (235, 245, 255),
        "girlfriend": (255, 240, 248),
        "dentist": (245, 255, 245),
    }.get(style, (245, 245, 245))
    rr(surf, pg.Rect(0, 0, size, size), bg, r=22)
    pg.draw.rect(surf, OUTLINE, pg.Rect(0, 0, size, size), width=6, border_radius=22)

    cx, cy = size // 2, size // 2 + 14

    # head
    skin = (255, 222, 190)
    pg.draw.circle(surf, OUTLINE, (cx, cy), 74)
    pg.draw.circle(surf, skin, (cx, cy), 70)

    # hair / hat variants
    if style == "analyst":
        # side part hair + glasses
        pg.draw.arc(surf, (60, 40, 30), pg.Rect(cx - 70, cy - 86, 140, 120), math.pi, 2 * math.pi, 18)
        pg.draw.rect(surf, (60, 40, 30), pg.Rect(cx - 70, cy - 70, 140, 40), border_radius=20)
    elif style == "girlfriend":
        # bangs + long hair
        pg.draw.circle(surf, (80, 45, 35), (cx - 55, cy + 10), 62)
        pg.draw.circle(surf, (80, 45, 35), (cx + 55, cy + 10), 62)
        pg.draw.arc(surf, (80, 45, 35), pg.Rect(cx - 78, cy - 92, 156, 110), math.pi, 2*math.pi, 22)
    elif style == "dentist":
        # cap
        pg.draw.rect(surf, (70, 120, 170), pg.Rect(cx - 78, cy - 92, 156, 52), border_radius=18)
        pg.draw.rect(surf, (70, 120, 170), pg.Rect(cx - 56, cy - 62, 112, 18), border_radius=12)

    # eyes
    eye_y = cy - 14
    for ex in (-28, 28):
        pg.draw.circle(surf, (255, 255, 255), (cx + ex, eye_y), 14)
        pg.draw.circle(surf, OUTLINE, (cx + ex, eye_y), 14, 3)
        pg.draw.circle(surf, (40, 70, 120), (cx + ex, eye_y), 6)
        pg.draw.circle(surf, (0, 0, 0), (cx + ex, eye_y), 3)

    # glasses for analyst
    if style == "analyst":
        pg.draw.rect(surf, OUTLINE, pg.Rect(cx - 54, eye_y - 16, 44, 32), 3, border_radius=10)
        pg.draw.rect(surf, OUTLINE, pg.Rect(cx + 10, eye_y - 16, 44, 32), 3, border_radius=10)
        pg.draw.line(surf, OUTLINE, (cx - 10, eye_y), (cx + 10, eye_y), 3)

    # mouth
    if style == "dentist":
        # big smile
        pg.draw.arc(surf, OUTLINE, pg.Rect(cx - 34, cy + 8, 68, 44), 0, math.pi, 4)
        pg.draw.rect(surf, (255, 255, 255), pg.Rect(cx - 26, cy + 18, 52, 18), border_radius=6)
        pg.draw.rect(surf, OUTLINE, pg.Rect(cx - 26, cy + 18, 52, 18), 3, border_radius=6)
    else:
        pg.draw.arc(surf, OUTLINE, pg.Rect(cx - 28, cy + 16, 56, 28), 0, math.pi, 4)

    # clothing
    body = pg.Rect(cx - 84, cy + 58, 168, 86)
    if style == "analyst":
        rr(surf, body, (90, 120, 200), r=24)
        pg.draw.rect(surf, OUTLINE, body, 5, border_radius=24)
        # tie
        pg.draw.polygon(surf, (200, 60, 60), [(cx, cy+74), (cx-10, cy+96), (cx, cy+132), (cx+10, cy+96)])
        pg.draw.polygon(surf, OUTLINE, [(cx, cy+74), (cx-10, cy+96), (cx, cy+132), (cx+10, cy+96)], 3)
    elif style == "girlfriend":
        rr(surf, body, (235, 110, 165), r=24)
        pg.draw.rect(surf, OUTLINE, body, 5, border_radius=24)
        # little heart pin
        pg.draw.circle(surf, (255, 255, 255), (cx - 40, cy + 92), 10)
        pg.draw.circle(surf, OUTLINE, (cx - 40, cy + 92), 10, 3)
    elif style == "dentist":
        rr(surf, body, (120, 210, 150), r=24)
        pg.draw.rect(surf, OUTLINE, body, 5, border_radius=24)
        # tooth icon
        pg.draw.circle(surf, (255, 255, 255), (cx + 46, cy + 92), 14)
        pg.draw.circle(surf, OUTLINE, (cx + 46, cy + 92), 14, 3)

    return surf


def save_portraits(asset_dir: str):
    ensure_dir(asset_dir)
    for style in ("analyst", "girlfriend", "dentist"):
        fn = os.path.join(asset_dir, f"{style}.png")
        if not os.path.exists(fn):
            s = draw_portrait(style)
            pg.image.save(s, fn)


# -----------------------------
# Stock round model
# -----------------------------
@dataclass
class RoundParams:
    mu: float
    sigma: float
    seconds: int

@dataclass
class Position:
    side: str = "FLAT"          # "LONG" or "FLAT"
    entry_price: Optional[float] = None
    bet: float = 100_000.0

    def is_long(self) -> bool:
        return self.side == "LONG" and self.entry_price is not None

    def go_long(self, price: float):
        self.side = "LONG"
        self.entry_price = price

    def go_flat(self):
        self.side = "FLAT"
        self.entry_price = None


class StockRound:
    def __init__(self, params: RoundParams, spinner: GaltonSpinner):
        self.params = params
        self.spinner = spinner
        self.t = 0.0
        self.done = False

        self.prices: List[float] = [START_PRICE]
        self.returns: List[float] = []

        self.total_steps = int(params.seconds * STEP_HZ)

    @property
    def price(self) -> float:
        return self.prices[-1]

    def step(self):
        if self.done:
            return
        r = self.spinner.sample_return(self.params.mu, self.params.sigma, DT)
        self.returns.append(r)
        new_price = self.prices[-1] * (1.0 + r)
        # prevent negative or crazy small
        new_price = max(1.0, new_price)
        self.prices.append(new_price)

        if len(self.prices) >= self.total_steps + 1:
            self.done = True


# -----------------------------
# UI components
# -----------------------------
class Button:
    def __init__(self, rect: pg.Rect, label: str):
        self.rect = rect
        self.label = label
        self.hover = False

    def draw(self, surf, font):
        fill = (255, 255, 255) if not self.hover else (250, 252, 255)
        rro(surf, self.rect, fill, r=14, w=4)
        draw_text_center(surf, self.label, self.rect.center, font, color=INK)

    def handle(self, event) -> bool:
        if event.type == pg.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False


def chart_points(prices: List[float], rect: pg.Rect) -> List[Tuple[int, int]]:
    if len(prices) < 2:
        return []
    lo = min(prices)
    hi = max(prices)
    if hi <= lo:
        hi = lo + 1e-6

    xs = []
    n = len(prices)
    for i, p in enumerate(prices):
        x = rect.x + int(i * (rect.w - 1) / (n - 1))
        y_norm = (p - lo) / (hi - lo)   # 0..1
        y = rect.bottom - int(y_norm * (rect.h - 1))
        xs.append((x, y))
    return xs


# -----------------------------
# Game states
# -----------------------------
STATE_CONSULT = "consult"
STATE_ROUND = "round"
STATE_RESULTS = "results"

class StockGaltonGame:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((W, H))
        pg.display.set_caption("Stock Galton MVP")
        self.clock = pg.time.Clock()

        self.font = pg.font.SysFont("comicsansms", 26)
        self.font_big = pg.font.SysFont("comicsansms", 44, bold=True)
        self.font_small = pg.font.SysFont("comicsansms", 20)

        self.asset_dir = os.path.join(os.path.dirname(__file__), "assets_stock_galton")
        save_portraits(self.asset_dir)

        self.spinner = GaltonSpinner(rows=GALTON_ROWS)
        self.characters = [
            Character("1", "Analyst", "CFA (probably)", bias=0.01, noise=0.03, style="analyst"),
            Character("2", "Girlfriend", "Vibes Department", bias=0.02, noise=0.06, style="girlfriend"),
            Character("3", "Dentist", "Pain & Mean Reversion", bias=-0.01, noise=0.05, style="dentist"),
        ]

        self.balance = BALANCE_START
        self.position = Position(bet=100_000.0)

        self.state = STATE_CONSULT
        self.params = self._new_round_params()
        self.round = StockRound(self.params, self.spinner)

        self.last_speech: Optional[str] = None
        self.last_speaker: Optional[Character] = None

        # buttons
        self.btn_start = Button(pg.Rect(W - 260, H - 90, 220, 56), "SPACE: Start Round")
        self.btn_next = Button(pg.Rect(W - 260, H - 90, 220, 56), "R: Next Round")

        # portraits cache
        self.portraits = {
            c.style: pg.image.load(os.path.join(self.asset_dir, f"{c.style}.png")).convert_alpha()
            for c in self.characters
        }

        # timing for round steps
        self._acc = 0.0

        # settlement info
        self.last_pnl = 0.0
        self.last_ret = 0.0

    def _new_round_params(self) -> RoundParams:
        mu = random.uniform(*MU_RANGE) / 252.0 * 252.0   # keep in "per round" scale, still random
        sigma = random.uniform(*SIGMA_RANGE)
        seconds = ROUND_SECONDS_DEFAULT
        return RoundParams(mu=mu, sigma=sigma, seconds=seconds)

    # --------- inputs ---------
    def handle_events(self) -> bool:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return False
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    return False

                if self.state == STATE_CONSULT:
                    if event.key == pg.K_SPACE:
                        self.start_round()
                    if event.unicode in ("1", "2", "3"):
                        self.consult(event.unicode)

                elif self.state == STATE_ROUND:
                    if event.key == pg.K_b:
                        # buy
                        if not self.position.is_long():
                            self.position.go_long(self.round.price)
                    if event.key == pg.K_s:
                        # sell/flat
                        self.position.go_flat()

                    if event.key == pg.K_UP:
                        self.position.bet = clamp(self.position.bet + BET_STEP, BET_MIN, BET_MAX)
                    if event.key == pg.K_DOWN:
                        self.position.bet = clamp(self.position.bet - BET_STEP, BET_MIN, BET_MAX)

                elif self.state == STATE_RESULTS:
                    if event.key == pg.K_r:
                        self.next_round()

            # mouse hover/buttons
            if self.state == STATE_CONSULT:
                self.btn_start.handle(event)
            if self.state == STATE_RESULTS:
                self.btn_next.handle(event)

        return True

    def consult(self, key: str):
        c = next((x for x in self.characters if x.key == key), None)
        if not c:
            return
        self.last_speaker = c
        self.last_speech = c.speak(self.params.mu, self.params.sigma)

    def start_round(self):
        self.state = STATE_ROUND
        self.position.go_flat()
        self._acc = 0.0

    def next_round(self):
        self.params = self._new_round_params()
        self.round = StockRound(self.params, self.spinner)
        self.state = STATE_CONSULT
        self.last_speech = None
        self.last_speaker = None
        self.position.go_flat()

    # --------- update ---------
    def update(self, dt: float):
        if self.state == STATE_ROUND:
            self._acc += dt
            while self._acc >= (1.0 / STEP_HZ) and not self.round.done:
                self._acc -= (1.0 / STEP_HZ)
                self.round.step()

            if self.round.done:
                self.settle_round()
                self.state = STATE_RESULTS

    def settle_round(self):
        final_price = self.round.prices[-1]
        self.last_ret = (final_price / self.round.prices[0]) - 1.0

        pnl = 0.0
        if self.position.is_long():
            pnl = self.position.bet * ((final_price / self.position.entry_price) - 1.0)

        self.balance += pnl
        self.last_pnl = pnl

    # --------- draw ---------
    def draw_top_bar(self):
        bar = pg.Rect(0, 0, W, 64)
        rr(self.screen, bar, (255, 255, 255), r=0)
        pg.draw.line(self.screen, (220, 225, 235), (0, 64), (W, 64), 2)

        draw_text(self.screen, "Stock Galton", (18, 16), self.font_big, color=INK)

        right = f"Balance: {fmt_money(self.balance)}"
        draw_text(self.screen, right, (W - 18 - self.font.size(right)[0], 20), self.font, color=INK)

    def draw_consult(self):
        self.screen.fill((210, 230, 255))
        self.draw_top_bar()

        draw_text(self.screen, "Pre-round: consult your 'experts' then press SPACE to start.",
                  (20, 90), self.font, color=INK)

        # character cards
        card_w, card_h = 340, 420
        gap = 30
        x0 = 40
        y0 = 140

        for i, c in enumerate(self.characters):
            rect = pg.Rect(x0 + i * (card_w + gap), y0, card_w, card_h)
            rro(self.screen, rect, PANEL, r=18, w=5)

            # portrait
            img = self.portraits[c.style]
            p = img.get_rect()
            p.center = (rect.centerx, rect.y + 130)
            self.screen.blit(img, p)

            draw_text_center(self.screen, f"[{c.key}] {c.name}", (rect.centerx, rect.y + 250), self.font, color=INK)
            draw_text_center(self.screen, c.title, (rect.centerx, rect.y + 284), self.font_small, color=MUTED)

            hint = "Press key to consult"
            draw_text_center(self.screen, hint, (rect.centerx, rect.y + 330), self.font_small, color=BLUE)

        # bubble
        bubble = pg.Rect(40, 580, W - 80, 110)
        rro(self.screen, bubble, (255, 255, 255), r=18, w=5)

        if self.last_speech:
            lines = self.last_speech.split("\n")
            yy = bubble.y + 14
            for ln in lines:
                draw_text(self.screen, ln, (bubble.x + 16, yy), self.font_small, color=INK)
                yy += 26
        else:
            draw_text(self.screen, "No one has spoken yet. Try keys 1 / 2 / 3.",
                      (bubble.x + 16, bubble.y + 40), self.font_small, color=MUTED)

        # start button (visual only)
        self.btn_start.draw(self.screen, self.font_small)

        # small "round unknown" teaser
        teaser = "The market is about to do something. Nobody knows what. Probably."
        draw_text(self.screen, teaser, (20, 120), self.font_small, color=MUTED)

    def draw_round(self):
        self.screen.fill((235, 242, 250))
        self.draw_top_bar()

        # chart
        chart_rect = pg.Rect(40, 110, W - 80, 420)
        rro(self.screen, chart_rect, CHART_BG, r=18, w=5)

        # axis labels
        draw_text(self.screen, "Price", (chart_rect.x + 14, chart_rect.y + 10), self.font_small, color=MUTED)

        pts = chart_points(self.round.prices, chart_rect.inflate(-2*CHART_PAD, -2*CHART_PAD))
        if len(pts) >= 2:
            # line
            pg.draw.lines(self.screen, BLUE, False, pts, 3)
            # last dot
            pg.draw.circle(self.screen, OUTLINE, pts[-1], 7)
            pg.draw.circle(self.screen, (255, 255, 255), pts[-1], 5)

        # current price label
        price_txt = f"{self.round.price:,.2f}"
        price_txt = price_txt.replace(",", "'")
        draw_text(self.screen, f"Last: {price_txt}", (chart_rect.x + 14, chart_rect.y + 40), self.font, color=INK)

        # progress bar
        steps = len(self.round.prices) - 1
        prog = steps / max(1, self.round.total_steps)
        prog_rect = pg.Rect(chart_rect.x, chart_rect.bottom + 14, chart_rect.w, 16)
        rr(self.screen, prog_rect, (220, 225, 235), r=10)
        rr(self.screen, pg.Rect(prog_rect.x, prog_rect.y, int(prog_rect.w * prog), prog_rect.h), (120, 180, 255), r=10)

        # trading panel
        panel = pg.Rect(40, 570, W - 80, 120)
        rro(self.screen, panel, (255, 255, 255), r=18, w=5)

        side_color = GREEN if self.position.is_long() else MUTED
        side_txt = "LONG" if self.position.is_long() else "FLAT"
        draw_text(self.screen, f"Position: {side_txt}", (panel.x + 16, panel.y + 18), self.font, color=side_color)

        if self.position.is_long():
            draw_text(self.screen, f"Entry: {self.position.entry_price:,.2f}".replace(",", "'"),
                      (panel.x + 16, panel.y + 54), self.font_small, color=MUTED)
            unreal = self.position.bet * ((self.round.price / self.position.entry_price) - 1.0)
            draw_text(self.screen, f"Unrealized: {fmt_money(unreal)}",
                      (panel.x + 16, panel.y + 78), self.font_small, color=(GREEN if unreal >= 0 else RED))

        draw_text(self.screen, f"Bet: {fmt_money(self.position.bet)}  (UP/DOWN)", (panel.x + 360, panel.y + 18), self.font, color=INK)
        draw_text(self.screen, "Controls: B=Buy/Long  S=Sell/Flat", (panel.x + 360, panel.y + 60), self.font_small, color=MUTED)

    def draw_results(self):
        self.screen.fill((225, 235, 255))
        self.draw_top_bar()

        card = pg.Rect(120, 140, W - 240, 450)
        rro(self.screen, card, (255, 255, 255), r=22, w=6)

        # headline
        final_price = self.round.prices[-1]
        move = (final_price / self.round.prices[0]) - 1.0

        headline = "Round Finished!"
        draw_text_center(self.screen, headline, (card.centerx, card.y + 70), self.font_big, color=INK)

        draw_text_center(self.screen, f"Stock move: {fmt_pct(move)}", (card.centerx, card.y + 150), self.font, color=(GREEN if move >= 0 else RED))
        draw_text_center(self.screen, f"Your P&L: {fmt_money(self.last_pnl)}", (card.centerx, card.y + 200), self.font, color=(GREEN if self.last_pnl >= 0 else RED))
        draw_text_center(self.screen, f"New balance: {fmt_money(self.balance)}", (card.centerx, card.y + 250), self.font, color=INK)

        # small story text
        story = "You feel emotions. The market feels nothing."
        draw_text_center(self.screen, story, (card.centerx, card.y + 320), self.font_small, color=MUTED)

        # replay
        self.btn_next.draw(self.screen, self.font_small)

        draw_text(self.screen, "Tip: consult again — each character lies differently.", (120, 620), self.font_small, color=MUTED)

    def draw(self):
        if self.state == STATE_CONSULT:
            self.draw_consult()
        elif self.state == STATE_ROUND:
            self.draw_round()
        elif self.state == STATE_RESULTS:
            self.draw_results()

        pg.display.flip()

    # --------- main loop ---------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            running = self.handle_events()
            self.update(dt)
            self.draw()

        pg.quit()


def main():
    StockGaltonGame().run()


if __name__ == "__main__":
    main()
