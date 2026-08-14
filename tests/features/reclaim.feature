Feature: Reclaiming space, reversibly

  Nothing is deleted. Reclaiming moves paths into a quarantine directory beside a
  manifest recording where each came from, and `undo` puts them back. Emptying
  quarantine is a separate act the person performs, with the whole plan in front
  of them and no agent involved.

  A tool that decides what to delete from a model's judgement has to be
  reversible, because the judgement is sometimes wrong — that is the whole reason
  the verdicts exist.

  Background:
    Given a machine that looks like a developer's Mac
    And the machine has been surveyed

  Scenario: Approving an item moves it out of the way rather than deleting it
    When I reclaim "Sites/client-app/node_modules"
    Then "Sites/client-app/node_modules" is gone from where it was
    And it is sitting in quarantine
    And nothing was deleted

  Scenario: Undo puts everything back exactly where it came from
    When I reclaim "Sites/client-app/node_modules"
    And I undo
    Then "Sites/client-app/node_modules" is back where it was
    And it still holds everything it held before
    And quarantine is empty

  Scenario: Reclaiming reports what it actually freed
    When I reclaim "Sites/client-app/node_modules"
    Then it reports freeing the size of "Sites/client-app/node_modules"

  Scenario: What a proposal excludes is left exactly where it is
    When I reclaim "Sites/client-app" but not "Sites/client-app/src"
    Then "Sites/client-app/src" is back where it was
    And "Sites/client-app/src" is not in quarantine

  Scenario: Something irreplaceable is moved aside like anything else, and recorded as what it is
    When I reclaim ".ssh"
    Then ".ssh" is gone from where it was
    And the manifest records ".ssh" as irreplaceable
    When I undo
    Then ".ssh" is back where it was

  Scenario: Two reclaims are both remembered
    When I reclaim "Sites/client-app/node_modules"
    And I reclaim "Library/Caches"
    Then quarantine holds 2 items

  Scenario: Undo brings back everything, not just the last one
    When I reclaim "Sites/client-app/node_modules"
    And I reclaim "Library/Caches"
    And I undo
    Then "Sites/client-app/node_modules" is back where it was
    And "Library/Caches" is back where it was
    And quarantine is empty
