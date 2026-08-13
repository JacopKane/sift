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
    When I try to put "Documents" in the basket
    Then it warns that "Documents" cannot be replaced
    And "Documents" is back where it was

  Scenario: Insisting is enough, because it is your disk
    When I insist on putting "Documents" in the basket
    And I empty the basket
    Then "Documents" is gone from where it was
    And it is sitting in quarantine
    And the receipt records that it was overridden

  Scenario: Even an overridden delete can be taken back
    When I insist on putting "Documents" in the basket
    And I empty the basket
    And I undo
    Then "Documents" is back where it was
    And it still holds everything it held before

  Scenario: A basket of several goes in one go
    When I put "Sites/client-app/node_modules" in the basket
    And I put "Library/Caches" in the basket
    And I empty the basket
    Then quarantine holds 2 items
    And it reports freeing what the basket held
