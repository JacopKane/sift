Feature: Asking you when it genuinely cannot tell

  The whole product rests on one claim: it asks rather than guesses. Everywhere
  else that means asking the filesystem. Here it means asking the person, because
  some things were never written to the disk — whether last year's client folder
  still matters is not recoverable by any amount of scanning.

  The graph stops and waits. A question is only worth interrupting for when it is
  genuinely unresolved, big enough to matter, and not already settled by a rule —
  a tool that asks about everything is a tool nobody answers.

  Background:
    Given a machine that looks like a developer's Mac
    And the machine has been surveyed

  Scenario: A run with nothing ambiguous never interrupts
    When the review runs over things the rules already settled
    Then it finishes without asking anything

  @slow
  Scenario: An opaque folder large enough to matter becomes a question
    When the review runs
    Then it stops and asks about "Archive"
    And the question says what is inside it
    And no plan is produced while it is waiting

  @slow
  Scenario: Answering resumes the same run rather than starting over
    When the review runs
    And I answer that "Archive" is old client work I no longer need
    Then the run finishes
    And "Archive" ends up regenerable
    And the survey was not walked a second time

  @slow
  Scenario: Saying it matters is respected
    When the review runs
    And I answer that "Archive" is work I still need
    Then the run finishes
    And "Archive" ends up irreplaceable
    And "Archive" is not proposed for deletion
