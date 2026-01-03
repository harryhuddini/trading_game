# ui/widgets/chart_widget.py
import pygame


class ChartWidget:
    def __init__(self, rect):
        self.rect = rect

    def draw(self, surface, prices):
        if len(prices) < 2:
            return

        min_p = min(prices)
        max_p = max(prices)
        span = max(max_p - min_p, 1e-6)

        points = []
        for i, p in enumerate(prices):
            x = self.rect.left + i / (len(prices) - 1) * self.rect.width
            y = self.rect.bottom - (p - min_p) / span * self.rect.height
            points.append((x, y))

        pygame.draw.rect(surface, (60, 60, 60), self.rect, 1)
        pygame.draw.lines(surface, (0, 220, 0), False, points, 2)

    def draw_marks(self, surface, prices, marks):
        if not prices:
            return

        min_p = min(prices)
        max_p = max(prices)
        span = max(max_p - min_p, 1e-6)

        for idx, price, side in marks:
            if idx >= len(prices):
                continue

            x = self.rect.left + idx / (len(prices) - 1) * self.rect.width
            y = self.rect.bottom - (price - min_p) / span * self.rect.height

            color = (0, 200, 0) if side == "BUY" else (200, 60, 60)
            pygame.draw.circle(surface, color, (int(x), int(y)), 6)

            label = "B" if side == "BUY" else "S"
            font = pygame.font.SysFont("Arial", 14)
            txt = font.render(label, True, (0, 0, 0))
            surface.blit(txt, (x + 6, y - 6))
