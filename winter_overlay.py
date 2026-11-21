import math
import random
import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSColor,
    NSEvent,
    NSMakePoint,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSScreen,
    NSStatusBar,
    NSVariableStatusItemLength,
    NSView,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
)
from Foundation import NSObject, NSTimer
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGDesktopWindowLevel,
    kCGNullWindowID,
    kCGWindowListOptionOnScreenOnly,
)


def get_dock_bounds(screen_width, default_height):
    """Detect the horizontal [x_start, x_end] span and height of the bottom macOS Dock."""
    window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    if window_list:
        for win in window_list:
            if win.get("kCGWindowOwnerName") == "Dock":
                bounds = win.get("kCGWindowBounds", {})
                w = float(bounds.get("Width", 0))
                h = float(bounds.get("Height", 0))
                x = float(bounds.get("X", 0))
                if 100 < w < screen_width and 20 < h < 200:
                    return int(x), int(x + w), h

    margin = int(screen_width * 0.05)
    return margin, int(screen_width - margin), default_height


class AppController(NSObject):
    """Manages the top menu bar icon and controls the snow overlay."""

    def initWithView_(self, view):
        self = objc.super(AppController, self).init()
        if self is None:
            return None

        self.view = view
        self.paused = False

        # Create a status bar item in the top-right macOS menu bar
        status_bar = NSStatusBar.systemStatusBar()
        self.status_item = status_bar.statusItemWithLength_(NSVariableStatusItemLength)
        self.status_item.button().setTitle_("❄")

        menu = NSMenu.alloc().init()

        self.pause_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Pause Snow", "togglePause:", ""
        )
        self.pause_item.setTarget_(self)
        menu.addItem_(self.pause_item)

        clear_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Clear Dock Snow", "clearSnow:", ""
        )
        clear_item.setTarget_(self)
        menu.addItem_(clear_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)
        return self

    def togglePause_(self, sender):
        self.paused = not self.paused
        self.view.is_paused = self.paused
        self.pause_item.setTitle_("Resume Snow" if self.paused else "Pause Snow")

    def clearSnow_(self, sender):
        self.view.reset_snowbank()

    def quitApp_(self, sender):
        NSApplication.sharedApplication().terminate_(None)


class SnowOverlayView(NSView):
    def initWithFrame_dockHeight_(self, frame, dock_height):
        self = objc.super(SnowOverlayView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.width = int(frame.size.width)
        self.height = int(frame.size.height)
        self.tick_count = 0
        self.is_paused = False

        self.dock_x1, self.dock_x2, detected_h = get_dock_bounds(self.width, float(dock_height))
        self.dock_height = float(dock_height) if dock_height > 0 else detected_h
        self.max_snow_height = self.dock_height + 75.0

        self.floor = [self.dock_height] * self.width
        # Put 320 flakes in the pool (about half are staggered above the screen at any moment)
        self.flakes = [self._new_flake(initial=True) for _ in range(320)]

        # Interactive fairy light bulbs: [base_x, base_y, dx, dy, vx, vy, color, phase_idx]
        self.bulbs = []
        colors = [
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.25, 0.25, 0.95),  # Red
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.25, 0.9, 0.45, 0.95),  # Green
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.85, 0.2, 0.95),   # Yellow
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 0.7, 1.0, 0.95),    # Blue
        ]
        spacing = 48
        for i, x in enumerate(range(24, self.width, spacing)):
            sag = math.sin((x % 192) / 192.0 * math.pi) * 14
            y = self.height - 28 - sag
            self.bulbs.append([float(x), float(y), 0.0, 0.0, 0.0, 0.0, colors[i % len(colors)], i])

        self.prev_mouse = NSEvent.mouseLocation()

        # Run at 30 FPS for smooth animation with minimal CPU/battery impact
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / 30.0, self, "updateFrame:", None, True
        )
        return self

    def reset_snowbank(self):
        self.dock_x1, self.dock_x2, _ = get_dock_bounds(self.width, self.dock_height)
        self.floor = [self.dock_height] * self.width
        self.setNeedsDisplay_(True)

    def _new_flake(self, initial=False):
        # Stagger across a full screen height above the top edge so simultaneous hits never form waves
        start_y = (
            random.uniform(0, self.height * 2.0)
            if initial
            else random.uniform(self.height + 10.0, self.height * 2.0)
        )
        return [
            random.uniform(0, self.width - 1),
            start_y,
            random.uniform(1.6, 3.6),
            0.0,
            -random.uniform(2.2, 4.8),
            random.uniform(0, math.pi * 2),
        ]

    def _deposit_snow(self, x_float, radius):
        idx = int(x_float)
        if idx < self.dock_x1 or idx > self.dock_x2:
            return
        if self.floor[idx] >= self.max_snow_height:
            return

        edge_dist = min(idx - self.dock_x1, self.dock_x2 - idx)
        edge_factor = min(1.0, edge_dist / 18.0)
        self.floor[idx] += radius * 0.65 * edge_factor

        for offset in range(-3, 4):
            i = idx + offset
            if self.dock_x1 <= i < self.dock_x2:
                diff = self.floor[i] - self.floor[i + 1]
                if abs(diff) > 1.2:
                    transfer = diff * 0.35
                    self.floor[i] -= transfer
                    self.floor[i + 1] += transfer

    def updateFrame_(self, timer):
        if self.is_paused:
            return

        self.tick_count += 1
        mouse_loc = NSEvent.mouseLocation()
        mx, my = mouse_loc.x, mouse_loc.y
        mouse_vx = max(-18.0, min(18.0, mx - self.prev_mouse.x))
        mouse_vy = max(-18.0, min(18.0, my - self.prev_mouse.y))
        self.prev_mouse = mouse_loc

        # 1. Fairy light spring physics
        for b in self.bulbs:
            bx = b[0] + b[2]
            by = b[1] + b[3]
            if abs(bx - mx) < 35.0 and abs(by - my) < 35.0:
                if math.hypot(bx - mx, by - my) < 34.0:
                    b[4] += mouse_vx * 0.45 + (bx - mx) * 0.1
                    b[5] += mouse_vy * 0.45 + (by - my) * 0.1

            b[4] = (b[4] - 0.16 * b[2]) * 0.88
            b[5] = (b[5] - 0.16 * b[3]) * 0.88
            b[2] += b[4]
            b[3] += b[5]

        # 2. Cursor shoveling snow on top of the Dock
        m_idx = int(mx)
        if self.dock_x1 <= m_idx <= self.dock_x2 and self.dock_height - 5 <= my < self.floor[m_idx] + 15:
            brush_radius = 35
            for offset in range(-brush_radius, brush_radius + 1):
                i = m_idx + offset
                if self.dock_x1 <= i <= self.dock_x2:
                    falloff = 1.0 - (abs(offset) / brush_radius) ** 2
                    target_h = max(self.dock_height, my - 6.0 * falloff)
                    if self.floor[i] > target_h:
                        removed = self.floor[i] - target_h
                        self.floor[i] = target_h
                        if removed > 0.8 and random.random() < 0.18 and len(self.flakes) < 240:
                            self.flakes.append([
                                float(i),
                                target_h + 4.0,
                                random.uniform(1.5, 3.0),
                                random.uniform(-4.0, 4.0),
                                random.uniform(3.0, 7.0),
                                random.uniform(0, math.pi * 2),
                            ])

        # 3. Update snowflakes
        i = 0
        while i < len(self.flakes):
            flake = self.flakes[i]
            flake[5] += 0.06
            flake[0] += math.sin(flake[5]) * 0.8 + flake[3]
            flake[1] += flake[4]
            flake[3] *= 0.92
            flake[4] = max(flake[4] - 0.2, -5.0)

            if flake[0] < 0:
                flake[0] += self.width
            elif flake[0] >= self.width:
                flake[0] -= self.width

            # Air repulsion from cursor (fast bounding-box pre-check before sqrt)
            dx = flake[0] - mx
            dy = flake[1] - my
            if -75.0 < dx < 75.0 and -75.0 < dy < 75.0:
                dist_sq = dx * dx + dy * dy
                if 0 < dist_sq < 5625.0:  # 75^2
                    dist = math.sqrt(dist_sq)
                    force = (75.0 - dist) / 75.0 * 5.0
                    flake[0] += (dx / dist) * force
                    flake[1] += (dy / dist) * force

            col = max(0, min(self.width - 1, int(flake[0])))
            on_dock = self.dock_x1 <= col <= self.dock_x2

            if on_dock and flake[1] <= self.floor[col] and flake[4] < 0:
                self._deposit_snow(flake[0], flake[2])
                if len(self.flakes) > 180:
                    self.flakes.pop(i)
                    continue
                self.flakes[i] = self._new_flake(initial=False)
            elif flake[1] <= 0:
                if len(self.flakes) > 180:
                    self.flakes.pop(i)
                    continue
                self.flakes[i] = self._new_flake(initial=False)

            i += 1

        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        # 1. Fairy light wire
        NSColor.colorWithCalibratedWhite_alpha_(0.15, 0.75).setStroke()
        wire = NSBezierPath.bezierPath()
        wire.setLineWidth_(1.5)
        for idx, b in enumerate(self.bulbs):
            pt = NSMakePoint(b[0] + b[2], b[1] + b[3] + 6)
            if idx == 0:
                wire.moveToPoint_(pt)
            else:
                wire.lineToPoint_(pt)
        wire.stroke()

        # 2. Glowing bulbs
        for b in self.bulbs:
            bx = b[0] + b[2]
            by = b[1] + b[3]
            color = b[6]
            idx = b[7]

            pulse = 0.65 + 0.35 * math.sin(self.tick_count * 0.14 + idx)
            color.colorWithAlphaComponent_(0.25 * pulse).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(bx - 10, by - 10, 20, 20)
            ).fill()

            color.colorWithAlphaComponent_(pulse).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(bx - 4, by - 5, 8, 10)
            ).fill()

        # 3. Batch all snowflakes into a single NSBezierPath for fast GPU/CPU rendering
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.88).setFill()
        snow_path = NSBezierPath.bezierPath()
        for x, y, r, _, _, _ in self.flakes:
            snow_path.appendBezierPathWithOvalInRect_(
                NSMakeRect(x - r, y - r, r * 2, r * 2)
            )
        snow_path.fill()

        # 4. Accumulated snowbank strictly spanning [dock_x1, dock_x2]
        if self.dock_x2 > self.dock_x1:
            snow_bank = NSBezierPath.bezierPath()
            snow_bank.moveToPoint_(NSMakePoint(self.dock_x1, self.dock_height))
            step = 4
            for x in range(self.dock_x1, self.dock_x2 + 1, step):
                snow_bank.lineToPoint_(NSMakePoint(x, self.floor[x]))
            snow_bank.lineToPoint_(NSMakePoint(self.dock_x2, self.dock_height))
            snow_bank.closePath()

            NSColor.colorWithCalibratedWhite_alpha_(0.96, 0.94).setFill()
            snow_bank.fill()


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    screen = NSScreen.mainScreen()
    screen_frame = screen.frame()
    visible_frame = screen.visibleFrame()
    dock_height = visible_frame.origin.y

    window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        screen_frame,
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        False,
    )
    window.setBackgroundColor_(NSColor.clearColor())
    window.setOpaque_(False)
    window.setHasShadow_(False)
    window.setLevel_(kCGDesktopWindowLevel + 1)
    window.setIgnoresMouseEvents_(True)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorStationary
    )

    view = SnowOverlayView.alloc().initWithFrame_dockHeight_(screen_frame, dock_height)
    window.setContentView_(view)
    window.orderFrontRegardless()

    # Keep a strong reference to controller so Python's GC does not remove the menu bar icon
    controller = AppController.alloc().initWithView_(view)  # noqa: F841

    app.run()


if __name__ == "__main__":
    main()