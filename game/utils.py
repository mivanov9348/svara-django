from .models import PlayerHand, Game, Card
import random

CARD_POINTS = {'7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}

def calculate_points(cards):
    if len(cards) != 3:
        return 0
    ranks = [card.rank for card in cards]
    suits = [card.suit for card in cards]
    if all(rank == '7' for rank in ranks):
        return 34
    if len(set(ranks)) == 1:
        return 3 * CARD_POINTS[ranks[0]]
    has_7c = any(card.rank == '7' and card.suit == '♣' for card in cards)
    if has_7c:
        other_cards = [card for card in cards if not (card.rank == '7' and card.suit == '♣')]
        points = 11
        for card in other_cards:
            points += CARD_POINTS[card.rank]
        return points
    aces = sum(1 for card in cards if card.rank == 'A')
    if aces >= 2:
        return aces * 11
    if len(set(suits)) == 1:
        return sum(CARD_POINTS[r] for r in ranks)
    return max(CARD_POINTS[r] for r in ranks)

def computer_dark_bet_decision(computer_hand, game):
    chips = computer_hand.player.chips
    if game.dark_bet == 0 and random.random() < 0.5:  # 50% chance to dark bet
        bet = min(10, chips)  # Small initial dark bet
        return 'dark_bet', bet, "Computer bets blindly with confidence!"
    elif game.dark_bet > 0 and chips >= game.dark_bet * 2:
        if random.random() < 0.7:  # 70% chance to double
            bet = game.dark_bet * 2
            return 'dark_bet', bet, "Computer doubles the dark bet!"
    return 'skip', 0, "Computer skips the dark bet."

def start_new_round(game):
    you = game.players.get(name='You')
    computer = game.players.get(name='Computer')
    if you.chips <= 0 or computer.chips <= 0:
        return False
    PlayerHand.objects.filter(game=game).delete()
    game.dealer = computer if game.dealer == you else you
    game.stage = 'dark_bet'
    game.pot = 0
    game.dark_bet = 0
    game.svara_pot = 0
    game.next_player = you if game.dealer == computer else computer  # Non-dealer bets first
    game.save()
    deck = list(Card.objects.all())
    your_hand = PlayerHand.objects.create(player=you, game=game)
    computer_hand = PlayerHand.objects.create(player=computer, game=game)
    your_cards = random.sample(deck, 3)
    your_hand.cards.set(your_cards)
    for card in your_cards:
        deck.remove(card)
    computer_cards = random.sample(deck, 3)
    computer_hand.cards.set(computer_cards)
    return True

def computer_betting_decision(computer_hand, game, min_bet):
    points = calculate_points(computer_hand.cards.all())
    chips = computer_hand.player.chips
    pot = game.pot
    if points >= 34:
        aggression = 0.5
        message = "Computer grins wickedly and goes big!"
    elif points >= 30:
        aggression = 0.3
        message = "Computer smirks and raises the stakes!"
    elif points >= 25:
        aggression = 0.15
        message = "Computer nods confidently and bets."
    elif points >= 20:
        aggression = 0.05
        message = "Computer tosses in a few chips cautiously."
    else:
        aggression = 0
        message = "Computer hesitates and folds."
    if points < 20 and chips > pot and random.random() < 0.1:
        aggression = 0.1
        message = "Computer smirks slyly and bluffs!"
    if aggression == 0 and min_bet > chips * 0.1:
        return 'fold', 0, message
    elif min_bet > 0 and chips >= min_bet:
        if random.random() < 0.5:  # 50% chance to call instead of raise
            return 'bet', min_bet, "Computer calls calmly."
        bet = max(min_bet, int(chips * aggression))
        return 'bet', min(bet, chips), message
    elif aggression > 0 and chips > 0:
        bet = int(chips * aggression)
        return 'bet', min(bet, chips), message
    return 'fold', 0, message