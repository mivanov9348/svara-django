# Константа за точките на картите
CARD_POINTS = {'7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}

def calculate_points(cards):
    """
    Изчислява точките на ръка от 3 карти според правилата на Свара.
    - Три седмици: 34 точки
    - Три еднакви: 3 пъти точките на картата
    - 7♣: 11 точки + сумата на другите карти
    - Два или три аса: брой аса * 11
    - Един костюм: сума на точките
    - Иначе: най-високата карта
    """
    if len(cards) != 3:
        return 0

    ranks = [card.rank for card in cards]
    suits = [card.suit for card in cards]

    if all(rank == '7' for rank in ranks):
        return 34

    if len(set(ranks)) == 1:
        return 3 * CARD_POINTS[ranks[0]]

    # Седмица спатия (7♣)
    has_7c = any(card.rank == '7' and card.suit == '♣' for card in cards)
    if has_7c:
        other_cards = [card for card in cards if not (card.rank == '7' and card.suit == '♣')]
        points = 11  # Бонус за 7♣
        for card in other_cards:
            points += CARD_POINTS[card.rank]
        return points

    aces = sum(1 for card in cards if card.rank == 'A')
    if aces >= 2:
        return aces * 11

    if len(set(suits)) == 1:
        return sum(CARD_POINTS[r] for r in ranks)

    return max(CARD_POINTS[r] for r in ranks)