Feature: Asking you when it genuinely cannot tell

  The whole product rests on one claim: it asks rather than guesses. Everywhere
  else that means asking the filesystem. Here it means asking the person, because
  some things were never written to the disk — whether last year's client folder
  still matters is not recoverable by any amount of scanning.

  These assert the graph's behaviour, not the model's opinion. Which folder comes
  back unresolved is a judgement that varies between runs and between providers;
  what must not vary is that whatever is unresolved and worth the interruption
  gets asked about, and that answering resumes rather than restarts.

  Background:
    Given a machine that looks like a developer's Mac
    And the machine has been surveyed

  Scenario: A run with nothing ambiguous never interrupts
    When the review runs over things the rules already settled
    Then it finishes without asking anything

  @slow
  Scenario: Whatever is left unresolved and big enough becomes a question
    When the review runs
    Then everything unresolved and worth asking about was asked about
    And nothing already settled by a rule was asked about
    And every question says what is inside what it asks about
    And no plan is produced while it is waiting

  @slow
  Scenario: Answering resumes the same run rather than starting over
    When the review runs
    And I answer that everything asked about is finished with
    Then the run finishes
    And everything I was asked about ends up regenerable
    And the survey was not walked a second time

  @slow
  Scenario: Saying it matters is respected
    When the review runs
    And I answer that everything asked about still matters
    Then the run finishes
    And everything I was asked about ends up irreplaceable
    And none of it is proposed for deletion
