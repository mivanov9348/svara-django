def calculate_points(cards):
    if len(cards) != 3:
        return 0

    ranks = [card.rank for card in cards]
    suits = [card.suit for card in cards]
    points = 0

    if all(rank == '7' for rank in ranks):
        return 34

    if len(set(ranks)) == 1:
        return 3 * {'7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}[ranks[0]]

    has_7c = any(card.rank == '7' and card.suit == '♣' for card in cards)
    if has_7c:
        other_cards = [card for card in cards if not (card.rank == '7' and card.suit == '♣')]
        points = 11
        for card in other_cards:
            points += {'7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}[card.rank]
        return points

    aces = sum(1 for card in cards if card.rank == 'A')
    if aces >= 2:
        return aces * 11

    if len(set(suits)) == 1:
        return sum({'7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}[r] for r in ranks)

    return max({'7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}[r] for r in ranks)