from src.game import Game
from src.breath_toggle_patch import apply_breath_toggle_patch


def main() -> None:
    apply_breath_toggle_patch(Game)
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
