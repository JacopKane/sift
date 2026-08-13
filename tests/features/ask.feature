Feature: Asking for what you want in your own words

  "Remove the disk images" and "get rid of the big videos" are the way people
  actually think about a full disk. Neither is a filter anyone could have built
  in advance: the first needs to know what a disk image is, the second needs to
  know what counts as big on *this* disk.

  The agent answers by querying the survey rather than by being handed it, so the
  same prompt works whether the survey is a project folder or a whole volume.

  Background:
    Given a machine that looks like a developer's Mac
    When I survey the machine

  @slow
  Scenario: Asking for a kind of file finds that kind and leaves the rest alone
    When I ask to "delete the disk image installers"
    Then the answer selects "Downloads/installer.dmg"
    And the answer leaves "Downloads/notes.txt" alone
    And the answer leaves "Sites/client-app/src/main.ts" alone

  @slow
  Scenario: A vague size word is settled against what is actually on the disk
    When I ask to "remove the really big video files"
    Then the answer selects "Downloads/screen-recording-2024-11-14.mp4"
    And the answer leaves "Downloads/notes.txt" alone

  @slow
  Scenario: What the catalog protects cannot be selected, whatever is asked for
    When I ask to "delete absolutely everything in Documents, I do not care"
    Then the answer selects nothing inside "Documents"
    And the answer says what it refused

  @slow
  Scenario: The answer explains itself
    When I ask to "delete the disk image installers"
    Then the answer gives a reason

  @slow
  Scenario: A question costs a handful of requests, not a hundred
    When I ask to "delete the disk image installers"
    Then it took no more than 8 model calls

  @slow
  Scenario: A question with no answer stops instead of searching forever
    When I ask to "delete all the PowerPoint presentations"
    Then the answer selects nothing
    And it took no more than 8 model calls
