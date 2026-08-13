Feature: Deciding for yourself what goes

  Sift proposes; it never decides. Anything it judges can be put in a basket and
  reclaimed, including the things it argued hardest against — it is your disk, and
  a tool that refuses outright is a tool you work around.

  What protection buys is a warning you cannot miss and a hand you have to force,
  not a locked door. The plan still never *proposes* anything protected. Putting
  one in the basket takes a deliberate override, and the receipt says so.

  Background:
    Given a machine that looks like a developer's Mac
    And the machine has been surveyed

  Scenario: Ordinary things go in the basket and out to quarantine
    When I put "Sites/client-app/node_modules" in the basket
    And I empty the basket
    Then "Sites/client-app/node_modules" is gone from where it was
    And it is sitting in quarantine

  Scenario: Protected things are refused unless you insist
    When I try to put ".ssh" in the basket
    Then it warns that ".ssh" cannot be replaced
    And ".ssh" is back where it was

  Scenario: Insisting is enough, because it is your disk
    When I insist on putting ".ssh" in the basket
    And I empty the basket
    Then ".ssh" is gone from where it was
    And it is sitting in quarantine
    And the receipt records that it was overridden

  Scenario: Even an overridden delete can be taken back
    When I insist on putting ".ssh" in the basket
    And I empty the basket
    And I undo
    Then ".ssh" is back where it was
    And it still holds everything it held before

  Scenario: A file inside a protected folder is protected too
    When I try to put ".ssh/id_ed25519" in the basket
    Then it warns that "id_ed25519" cannot be replaced
    And ".ssh/id_ed25519" is back where it was

  Scenario: Insisting on a file inside a protected folder is recorded as overridden
    When I insist on putting ".ssh/id_ed25519" in the basket
    And I empty the basket
    Then the receipt records that it was overridden

  Scenario: One item that cannot move does not strand the rest
    When I put "Sites/client-app/node_modules" in the basket
    And I put "Library/Caches" in the basket
    And something in the basket disappears before it is emptied
    And I empty the basket
    Then everything that could move did
    And the receipt says what could not

  Scenario: A basket of several goes in one go
    When I put "Sites/client-app/node_modules" in the basket
    And I put "Library/Caches" in the basket
    And I empty the basket
    Then quarantine holds 2 items
    And it reports freeing what the basket held
