Feature: Asking a model about what the catalog could not name

  The catalog settles whatever is knowable from a path. What survives is
  genuinely ambiguous — a folder of unknown provenance, a Downloads directory
  that could hold anything — and that is the only place a model earns its cost.

  These scenarios call the real model over the network. Nothing here is faked,
  because a fake would only ever prove the fake works, and the assertion worth
  having is that a folder of client deliverables never comes back disposable.

  Background:
    Given a machine that looks like a developer's Mac

  @slow
  Scenario: Every opaque directory comes back with a verdict and a reason
    When I survey the machine
    And I ask the model about the candidates
    Then every candidate is classified
    And every classification gives a reason
    And no classification invents a directory that was never offered

  @slow
  Scenario: A folder of client deliverables is never called disposable
    When I survey the machine
    And I ask the model about the candidates
    Then "Archive" is not regenerable

  @slow
  Scenario: An opaque folder of work is never called disposable
    When I survey the machine
    And I ask the model about the candidates
    Then "Sites/client-app/mockups" is not regenerable

  @slow
  Scenario: A directory holding both disposable and irreplaceable things is flagged for a human
    When I survey the machine
    And I ask the model about the candidates
    Then "Downloads" is not regenerable
    And "Downloads" needs review

  @slow
  Scenario: A directory of only irreplaceable things is not hedged as needing review
    When I survey the machine
    And I ask the model about the candidates
    Then "Archive" is irreplaceable

  @slow
  Scenario: Calling something regenerable means saying how to get it back
    When I survey the machine
    And I ask the model about the candidates
    Then anything called regenerable says how to restore it

  @slow
  Scenario: Every candidate is covered by a single call
    When I survey the machine
    And I ask the model about the candidates
    Then the model was called once

  @slow
  Scenario: The model reasons from what actually fills a directory
    When I survey the machine
    And I ask the model about the candidates
    Then the reason given for "Downloads" refers to what is inside it

  @slow
  Scenario: The model is told how long it has been since anything was opened
    Given a machine that looks like a developer's Mac
    When I survey the machine
    Then each candidate says when it was last opened
    And the model is shown that in words it can reason about
