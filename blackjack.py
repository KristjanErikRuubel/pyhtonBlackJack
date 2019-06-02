"""Simple game of blackjack."""

from textwrap import dedent

import requests


class Card:
    """Simple dataclass for holding card information."""

    def __init__(self, value: str, suit: str, code: str):
        """
        Constructor.

        :param value: Integer.
        :param suit: String.
        :param code: String.
        """
        self.value = value
        self.suit = suit
        self.code = code

    def __repr__(self):
        """
        Simple.

        :return: Code.
        """
        return self.code


class Hand:
    """Simple class for holding hand information."""

    def __init__(self):
        """Constructor."""
        self.cards = list()
        self.score = 0

    def add_card(self, card: Card):
        """
        Add card to hand.

        :param card: Object.
        :return: None.
        """
        self.cards.append(card)
        self.calculate_hand_score()

    def calculate_hand_score(self):
        """
        Calculate hand score.

        :return: Integer.
        """
        score_dict = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'JACK': 10,
                      'QUEEN': 10, 'KING': 10}
        new_score = 0
        count = 0

        for card in self.cards:
            if card.value in score_dict:
                new_score += score_dict[card.value]
            if card.value == 'ACE':
                count += 1
        if count:
            while count:
                if new_score + 11 > 21:
                    new_score += 1
                    count -= 1
                else:
                    new_score += 11
                    count -= 1
        self.score = new_score


class Deck:
    """Deck of cards. Provided via api over the network."""

    def __init__(self, shuffle=False):
        """
        Tell api to create a new deck.

        :param shuffle: if shuffle option is true, make new shuffled deck.
        """
        self.is_shuffled = shuffle
        if not self.is_shuffled:
            self.deck_id = requests.get('https://deckofcardsapi.com/api/deck/new').json()['deck_id']
        if self.is_shuffled:
            self.deck_id = requests.get('https://deckofcardsapi.com/api/deck/new/shuffle').json()['deck_id']

    def shuffle(self):
        """Shuffle the deck."""
        requests.get('https://deckofcardsapi.com/api/deck/' + self.deck_id + '/shuffle')
        self.is_shuffled = True

    def draw(self) -> Card:
        """
        Draw card from the deck.

        :return: card instance.
        """
        card_dict = requests.get('https://deckofcardsapi.com/api/deck/' + self.deck_id + '/draw').json()
        return Card(card_dict['cards'][0]['value'], card_dict['cards'][0]['suit'], card_dict['cards'][0]['code'])


class BlackjackController:
    """Blackjack controller. For controlling the game and data flow between view and database."""

    def __init__(self, deck: Deck, view: 'BlackjackView'):
        """
        Start new blackjack game.

        :param deck: deck to draw cards from.
        :param view: view to communicate with.
        """
        self.deck = deck
        self.view = view
        self.check_shuffle()
        self.player = Hand()
        self.dealer = Hand()
        score = self.draw_first_cards()
        if score == 21:
            view.player_won({"dealer": self.dealer, "player": self.player})
        else:
            lost = self.players_turn()
            if lost is None:
                if self.dealer.score == 21:
                    self.view.player_lost({"dealer": self.dealer, "player": self.player})
                    return
                else:
                    self.dealers_turn()

    def check_shuffle(self):
        """
        Shuffle.

        :return: None.
        """
        if not self.deck.is_shuffled:
            self.deck.shuffle()

    def draw_first_cards(self):
        """
        Draw Card from deck.

        :return: Score.
        """
        for i in range(4):
            if i % 2 == 0:
                self.player.add_card(self.deck.draw())
            else:
                self.dealer.add_card(self.deck.draw())
        return self.player.score

    def dealers_turn(self):
        """
        Dealer turn.

        :return: None.
        """
        while self.dealer.score <= self.player.score:
            self.dealer.add_card(self.deck.draw())
            if self.dealer.score == 21:
                self.view.player_lost({"dealer": self.dealer, "player": self.player})
                return
        if self.dealer.score < 21:
            self.view.player_lost({"dealer": self.dealer, "player": self.player})
            return
        if self.dealer.score > 22:
            self.view.player_won({"dealer": self.dealer, "player": self.player})
            return

    def players_turn(self):
        """
        Player turn.

        :return: Boolean.
        """
        while True:
            cmd = self.view.ask_next_move({"dealer": self.dealer, "player": self.player})
            if cmd == 'H':
                self.player.add_card(self.deck.draw())
                if self.player.score > 21:
                    self.view.player_lost({"dealer": self.dealer, "player": self.player})
                    return True
            elif cmd == 'S':
                return None
            if self.player.score == 21:
                self.view.player_won({"dealer": self.dealer, "player": self.player})
                return False
            if self.player.score > 22:
                self.view.player_lost({"dealer": self.dealer, "player": self.player})
                return False


class BlackjackView:
    """Minimalistic UI/view for the blackjack game."""

    def ask_next_move(self, state: dict) -> str:
        """
        Get next move from the player.

        :param state: dict with given structure: {"dealer": dealer, "player": player_hand_object}
        :return: parsed command that user has choses. String "H" for hit and "S" for stand
        """
        self.display_state(state)
        while True:
            action = input("Choose your next move hit(H) or stand(S) > ")
            if action.upper() in ["H", "S"]:
                return action.upper()
            print("Invalid command!")

    def player_lost(self, state):
        """
        Display player lost dialog to the user.

        :param state: dict with given structure: {"dealer": dealer, "player": player_hand_object}
        """
        self.display_state(state, final=True)
        print("You lost")

    def player_won(self, state):
        """
        Display player won dialog to the user.

        :param state: dict with given structure: {"dealer": dealer, "player": player_hand_object}
        """
        self.display_state(state, final=True)
        print("You won")

    def display_state(self, state, final=False):
        """
        Display state of the game for the user.

        :param state: dict with given structure: {"dealer": dealer, "player": player_hand_object}
        :param final: boolean if the given state is final state. True if game has been lost or won.
        """
        dealer_score = state["dealer"].score if final else "??"
        dealer_cards = state["dealer"].cards
        if not final:
            dealer_cards_hidden_last = [c.__repr__() for c in dealer_cards[:-1]] + ["??"]
            dealer_cards = f"[{','.join(dealer_cards_hidden_last)}]"

        player_score = state["player"].score
        player_cards = state["player"].cards
        print(dedent(
            f"""
            {"Dealer score":<15}: {dealer_score}
            {"Dealer hand":<15}: {dealer_cards}

            {"Your score":<15}: {player_score}
            {"Your hand":<15}: {player_cards}
            """
        ))
