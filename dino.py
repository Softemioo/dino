import time

from playwright.sync_api import sync_playwright

GAME_URL = "https://wayou.github.io/t-rex-runner/"
LOOP_DELAY = 0.01
JUMP_COOLDOWN = 0.08
JUMP_LEAD = 13.0
DUCK_LEAD = 15.0
MIN_LEAD = 60.0
MIN_DUCK_LEAD = 80.0

def get_state(page):
    try:
        return page.evaluate(
            """
            () => {
                const runner = window.Runner?.instance_;
                if (!runner) {
                    return { status: "NO_RUNNER" };
                }
                if (runner.crashed) {
                    return { status: "DEAD" };
                }
                if (!runner.playing) {
                    return { status: "NOT_PLAYING" };
                }
                const dinoX = runner.tRex.xPos;
                const obstacles = runner.horizon?.obstacles || [];
                let target = null;
                let bestDistance = Infinity;
                for (const obstacle of obstacles) {
                    const distance = obstacle.xPos - dinoX;
                    if (distance >= -obstacle.width && distance < bestDistance) {
                        bestDistance = distance;
                        target = obstacle;
                    }
                }
                if (!target) {
                    return {
                        status: "OK",
                        type: "NONE",
                        distance: 9999,
                        speed: runner.currentSpeed || 6,
                        yPos: 0
                    };
                }
                return {
                    status: "OK",
                    type: target.typeConfig?.type || "CACTUS",
                    distance: bestDistance,
                    speed: runner.currentSpeed || 6,
                    yPos: target.yPos || 0
                };
            }
            """
        )
    except Exception:
        return {"status": "ERROR"}

def start_game(page):
    page.locator("canvas").click()
    time.sleep(0.3)
    page.keyboard.press("Space")
    time.sleep(1.0)

def main():
    print("Запускаем программу...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--disable-gpu", "--disable-extensions"]
        )
        page = browser.new_page(viewport={"width": 800, "height": 600})
        print("Открываем игру...")
        page.goto(GAME_URL, wait_until="networkidle")
        print("Ждём загрузку игры...")
        time.sleep(2.5)

        start_game(page)
        print("Динозавр побежал. Бесконечный цикл запущен.")

        errors = 0
        cooldown = 0.0
        ducking = False
        while True:
            state = get_state(page)
            status = state.get("status")

            if status == "OK":
                errors = 0
                cooldown = max(0.0, cooldown - LOOP_DELAY)
                obstacle_type = state.get("type", "NONE")
                distance = state.get("distance", 9999)
                speed = state.get("speed", 6)
                y_pos = state.get("yPos", 0)

                duck_bird = (
                    obstacle_type == "PTERODACTYL"
                    and 55 < y_pos < 90
                    and distance < max(MIN_DUCK_LEAD, speed * DUCK_LEAD)
                )

                if duck_bird and not ducking:
                    page.keyboard.down("ArrowDown")
                    ducking = True
                elif not duck_bird and ducking:
                    page.keyboard.up("ArrowDown")
                    ducking = False

                if not ducking and cooldown <= 0:
                    need_jump = obstacle_type != "PTERODACTYL" or y_pos >= 90
                    threshold = max(MIN_LEAD, speed * JUMP_LEAD)
                    if need_jump and distance < threshold:
                        page.keyboard.press("Space")
                        cooldown = JUMP_COOLDOWN

            elif status == "DEAD":
                errors = 0
                if ducking:
                    page.keyboard.up("ArrowDown")
                    ducking = False
                time.sleep(1.0)
                page.keyboard.press("Space")
                time.sleep(1.0)
                cooldown = 0.0

            else:
                errors += 1
                if errors > 30:
                    print("Что-то пошло не так, перезагружаем страницу...")
                    if ducking:
                        page.keyboard.up("ArrowDown")
                        ducking = False
                    page.reload(wait_until="networkidle")
                    time.sleep(2.5)
                    start_game(page)
                    errors = 0
                    cooldown = 0.0
                else:
                    time.sleep(0.2)

            time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    main()