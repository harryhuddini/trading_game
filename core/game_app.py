# core/game_app.py
import time
import pygame

from core.game_state import GameState
from core.events import GameEvent
from ui.renderer import Renderer
from config.game_config import FPS, ROUND_DURATION_SEC

from simulation.galton_simulator import GaltonSimulator

from characters.analyst import Analyst
from characters.girlfriend import Girlfriend
from characters.dentist import Dentist

from trading.trader import Trader
from trading.settlement import settle
from ui.widgets.chart_widget import ChartWidget
from config.game_config import START_BALANCE, DEFAULT_BET

from config.speed_config import MARKET_HZ

EARLY_EXIT_THRESHOLD = 0.02  # 2% extra move after sell

class GameApp:
    def __init__(self):
        self.renderer = Renderer()
        self.state = GameState.MENU

        self.round_start_time = None
        self.running = True

        self.simulator = GaltonSimulator(
            start_price=100.0,
            pegs_per_step=25,
            volatility=0.35,
            drift=0.0,
            time_scale=8.0,
        )

        self.characters = [
            Analyst(),
            Girlfriend(),
            Dentist(),
        ]

        self.last_hints = []

        self.trader = Trader(START_BALANCE)
        self.trader.bet_size = DEFAULT_BET

        self.chart = ChartWidget(
            pygame.Rect(100, 100, 800, 300)
        )

        self.character_images = {
            "Analyst": pygame.image.load("assets/characters/analyst.png").convert_alpha(),
            "Girlfriend": pygame.image.load("assets/characters/girlfriend.png").convert_alpha(),
            "Dentist": pygame.image.load("assets/characters/dentist.png").convert_alpha(),
        }

        self._sim_acc = 0.0

        self.final_balance = START_BALANCE
        self._settled = False

        self.trade_marks = []  # list of (index, price, "BUY"/"SELL")

        self.reaction = None  # dict with text, color, until_ts
        self.last_consulted_character = None

        self.last_sell = None  # dict with price, index, pnl

        self.trust = {
            "Analyst": 0.0,
            "Girlfriend": 0.0,
            "Dentist": 0.0,
        }

    # -------------------------
    # Main loop
    # -------------------------
    def run(self):
        while self.running:
            events = self._poll_events()
            self._update(events)
            self._render()
            self.renderer.tick(FPS)

        self.renderer.shutdown()

    def _poll_events(self):
        game_events = []

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_events.append(GameEvent.QUIT)
                continue

            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_ESCAPE:
                game_events.append(GameEvent.QUIT)
                continue

            if self.state == GameState.MENU:
                if event.key in (pygame.K_SPACE, pygame.K_c):
                    game_events.append(("ENTER_CONSULT",))

            elif self.state == GameState.CONSULT:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    idx = event.key - pygame.K_1
                    self._consult_character(idx)
                elif event.key == pygame.K_SPACE:
                    game_events.append(GameEvent.START_GAME)

            elif self.state == GameState.ROUND:
                if event.key == pygame.K_b:
                    game_events.append(GameEvent.BUY)
                elif event.key == pygame.K_s:
                    game_events.append(GameEvent.SELL)
                elif event.key == pygame.K_UP:
                    game_events.append(("BET_UP",))
                elif event.key == pygame.K_DOWN:
                    game_events.append(("BET_DOWN",))

            elif self.state == GameState.RESULT:
                if event.key == pygame.K_r:
                    game_events.append(GameEvent.NEXT_ROUND)

        return game_events

    def _consult_character(self, idx):
        char = self.characters[idx]
        self.last_consulted_character = char

        hidden_state = {
            "drift": self.simulator.drift,
            "volatility": self.simulator.vol,
        }

        hint = char.give_hint(hidden_state)
        hint["name"] = char.name
        self.last_hints.append(hint)

    def _character_reaction_text(self, char_name: str, pnl: float, kind: str) -> str:
        if kind == "good":
            if char_name == "Analyst":
                return "Risk-adjusted alpha. Well done."
            if char_name == "Girlfriend":
                return "I *knew* you had it in you!"
            if char_name == "Dentist":
                return "Huh. That didn’t hurt."
            return "Nice trade."

        if kind == "bad":
            if char_name == "Analyst":
                return "That outcome was within expectations."
            if char_name == "Girlfriend":
                return "It’s okay… money isn’t everything."
            if char_name == "Dentist":
                return "This will hurt a little."
            return "Ouch."

        if kind == "early":
            if char_name == "Analyst":
                return "You exited before the thesis played out."
            if char_name == "Girlfriend":
                return "Why did you sell so fast?"
            if char_name == "Dentist":
                return "You stopped before the pain *or* the gain."
            return "Too early."

        return ""

    def _update(self, events):
        # Handle quit + instant events first
        for ev in events:
            if ev == GameEvent.QUIT:
                self.running = False
                return

        # -------------------------
        # State machine
        # -------------------------

        # MENU: go to CONSULT
        if self.state == GameState.MENU:
            for ev in events:
                if ev == ("ENTER_CONSULT",):
                    self.last_hints.clear()
                    self.state = GameState.CONSULT
                    return
            return

        # CONSULT: SPACE starts round
        if self.state == GameState.CONSULT:
            for ev in events:
                if ev == GameEvent.START_GAME:
                    self._enter_round()
                    return
            return

        # ROUND: always step sim every frame (no keypress required)
        if self.state == GameState.ROUND:
            dt_frame = 1.0 / FPS
            self._sim_acc += dt_frame

            # detect early exit
            if self.last_sell and self.last_sell["pnl"] > 0:
                current_price = self.simulator.path.last
                sell_price = self.last_sell["price"]

                if current_price > sell_price * (1 + EARLY_EXIT_THRESHOLD):
                    if self.last_consulted_character:
                        self._trigger_reaction("early", self.last_sell["pnl"])
                        self._update_trust(self.last_consulted_character.name, -0.1)
                    self.last_sell = None

            while self._sim_acc >= (1.0 / MARKET_HZ):
                self._sim_acc -= (1.0 / MARKET_HZ)
                self.simulator.step(1.0 / MARKET_HZ)

            # apply trading events
            for ev in events:
                if ev == GameEvent.BUY:
                    price = self.simulator.path.last
                    executed = self.trader.buy(price)
                    if executed:
                        self.trade_marks.append(
                            (len(self.simulator.path.prices) - 1, price, "BUY")
                        )
                elif ev == GameEvent.SELL:
                    price = self.simulator.path.last
                    executed = self.trader.sell(price)

                    if executed:
                        idx = len(self.simulator.path.prices) - 1
                        self.trade_marks.append((idx, price, "SELL"))

                        pnl = self.trader.realized_pnl

                        if pnl > 0:
                            self._update_trust(self.last_consulted_character.name, +0.1)
                        else:
                            self._update_trust(self.last_consulted_character.name, -0.15)

                        self.last_sell = {
                            "price": price,
                            "index": idx,
                            "pnl": pnl,
                        }

                        # immediate reaction (good / bad)
                        if self.last_consulted_character:
                            if pnl > 0:
                                self._trigger_reaction("good", pnl)
                            else:
                                self._trigger_reaction("bad", pnl)




                elif ev == ("BET_UP",):
                    self.trader.bet_size += 500

                elif ev == ("BET_DOWN",):
                    self.trader.bet_size = max(500, self.trader.bet_size - 500)

            # end round
            if time.time() - self.round_start_time >= ROUND_DURATION_SEC:
                self.state = GameState.RESULT
            return

        # RESULT: settle once, R to next round
        elif self.state == GameState.RESULT:
            if not self._settled:
                self.final_balance = settle(
                    self.trader, self.simulator.path.last
                )
                self._settled = True

            for ev in events:
                if ev == GameEvent.NEXT_ROUND:
                    self._settled = False
                    self.state = GameState.CONSULT
                    self.last_hints.clear()

        return

    def _enter_round(self):
        self.round_start_time = time.time()
        self.simulator.reset()
        self.trader.reset_round()
        self.trade_marks.clear()
        self._sim_acc = 0.0
        self.state = GameState.ROUND

    # -------------------------
    # Render
    # -------------------------
    def _render(self):
        self.renderer.clear()

        if self.state == GameState.MENU:
            self._render_menu()
        elif self.state == GameState.CONSULT:
            self._render_consult()
        elif self.state == GameState.ROUND:
            self._render_round()
        elif self.state == GameState.RESULT:
            self._render_result()

        self.renderer.present()

    def _render_consult(self):
        self.renderer.draw_text("CONSULT ADVISORS", 360, 60)
        self.renderer.draw_text("Press 1 / 2 / 3 to consult, SPACE to start",
                                250, 100)

        card_w = 220
        card_h = 260
        start_x = 120
        y = 160
        gap = 120

        for i, char in enumerate(self.characters):
            x = start_x + i * (card_w + gap)

            # Card background
            pygame.draw.rect(
                self.renderer.screen,
                (240, 240, 240),
                pygame.Rect(x, y, card_w, card_h),
                border_radius=12,
            )
            pygame.draw.rect(
                self.renderer.screen,
                (40, 40, 40),
                pygame.Rect(x, y, card_w, card_h),
                2,
                border_radius=12,
            )

            # Portrait
            img = self.character_images[char.name]
            img_rect = img.get_rect(center=(x + card_w // 2, y + 90))
            self.renderer.screen.blit(img, img_rect)

            # Name
            self.renderer.draw_text(
                f"[{i + 1}] {char.name}",
                x + 40,
                y + 180,
            )

            trust = self.trust.get(char.name, 0.0)
            bar_w = 120
            bar_x = x + 50
            bar_y = y + 210

            pygame.draw.rect(
                self.renderer.screen,
                (200, 200, 200),
                pygame.Rect(bar_x, bar_y, bar_w, 10),
            )

            fill = int((trust + 1) / 2 * bar_w)
            color = (0, 180, 0) if trust >= 0 else (200, 60, 60)

            pygame.draw.rect(
                self.renderer.screen,
                color,
                pygame.Rect(bar_x, bar_y, fill, 10),
            )

        # Show last hint (speech bubble style)
        if self.last_hints:
            hint = self.last_hints[-1]
            self.renderer.draw_text(
                f"{hint['name']}: {hint['text']}",
                120,
                460,
            )

    def _render_menu(self):
        self.renderer.draw_text("STOCK GALTON GAME", 350, 200)
        self.renderer.draw_text("SPACE = consult advisors", 340, 260)
        self.renderer.draw_text("C = consult advisors", 370, 300)

    def _render_round(self):
        price = self.simulator.path.last
        unreal = self.trader.mark_to_market(price)
        realized = self.trader.realized_pnl

        self.chart.draw(self.renderer.screen, self.simulator.path.prices)
        self.chart.draw_marks(
            self.renderer.screen,
            self.simulator.path.prices,
            self.trade_marks,
        )

        self.renderer.draw_text(f"Price: {price:0.2f}", 50, 430)
        self.renderer.draw_text(f"Bet: {self.trader.bet_size:,.0f}", 50, 460)
        self.renderer.draw_text(f"Unrealized: {unreal:,.0f}", 50, 490)
        self.renderer.draw_text(f"Realized: {realized:,.0f}", 50, 520)

        self._render_reaction()

    def _render_result(self):
        self.renderer.draw_text(
            "ROUND FINISHED", 380, 180
        )
        balance = getattr(self, "final_balance", self.trader.balance)
        self.renderer.draw_text(
            f"Balance: {balance:,.0f}",
            360, 240
        )

        self.renderer.draw_text(
            "Press R for next round",
            340, 290
        )

    def _render_reaction(self):
        if not self.reaction:
            return

        if time.time() > self.reaction["until"]:
            self.reaction = None
            return

        # bubble box
        rect = pygame.Rect(520, 420, 360, 90)
        pygame.draw.rect(
            self.renderer.screen,
            (255, 255, 255),
            rect,
            border_radius=14
        )
        pygame.draw.rect(
            self.renderer.screen,
            (60, 60, 60),
            rect,
            2,
            border_radius=14
        )

        self.renderer.draw_text(
            f"{self.reaction['name']}:",
            rect.x + 12,
            rect.y + 10
        )
        self.renderer.draw_text(
            self.reaction["text"],
            rect.x + 12,
            rect.y + 40
        )

    def _trigger_reaction(self, kind: str, pnl: float):
        char = self.last_consulted_character
        if not char:
            return

        self.reaction = {
            "name": char.name,
            "text": self._character_reaction_text(char.name, pnl, kind),
            "until": time.time() + 3.5,
            "kind": kind,
        }

    def _update_trust(self, char_name: str, delta: float):
        self.trust[char_name] = max(
            -1.0,
            min(1.0, self.trust.get(char_name, 0.0) + delta)
        )



