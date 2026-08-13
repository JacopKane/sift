Feature: Turning verdicts into something you can act on

  A list of directories is not a plan. Forty-seven node_modules folders scattered
  across three projects are one decision, not forty-seven, and what makes them one
  decision is the rule that recognised them. Grouping by rule is what turns a tree
  into something a person can read.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: Directories recognised by the same rule become a single decision
    Given a second project at "Sites/another-app" with its own node_modules
    When I survey the machine
    And I build a plan
    Then the plan has one proposal for "node_modules"
    And that proposal covers 2 directories
    And that proposal totals the size of both

  Scenario: The biggest reclaim is proposed first
    When I survey the machine
    And I build a plan
    Then the proposals are ordered largest first

  Scenario: Irreplaceable things are shown but never proposed
    When I survey the machine
    And I build a plan
    Then ".ssh" is not proposed
    And ".ssh" is listed as protected

  Scenario: Every proposal says how to get it back
    When I survey the machine
    And I build a plan
    Then every proposal says how to restore it

  Scenario: The reclaimable total promises only what is safe to promise
    When I survey the machine
    And I build a plan
    Then the reclaimable total counts only what can be rebuilt
    And what needs a human decision is counted separately
    And neither total counts anything protected
    And the reclaimable total is less than everything surveyed

  @slow
  Scenario: The plan never accounts for more bytes than the disk holds
    When I survey the machine
    And I ask the model about the candidates
    And I build a plan from what the model said
    Then the plan accounts for no more than was surveyed
    And nothing proposed contains something kept back

  Scenario: A directory inside something already proposed is not proposed twice
    When I survey the machine
    And I build a plan
    Then no proposal covers a path inside another proposal
    And "Library/Caches" is proposed
    And "Library/Caches/pip" is not proposed
