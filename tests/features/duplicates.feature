Feature: Finding the same thing twice

  A second lens over a survey that has already been walked. Two files with
  identical contents are one file and one copy, whatever they are called, and the
  copy costs you exactly as much as the original.

  Hashing every file on a disk would cost more than the survey did, so size is
  the filter: two files of different sizes cannot be identical, and on a real disk
  almost nothing shares a size. Only the handful that do are ever opened.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: Identical files are found however they are named
    Given a file "Downloads/report.pdf" holding "quarterly numbers"
    And a file "Archive/report-final.pdf" holding "quarterly numbers"
    When I look for duplicates
    Then "Downloads/report.pdf" and "Archive/report-final.pdf" are the same file
    And one of them is reported as reclaimable

  Scenario: Files that merely match in size are not called duplicates
    Given a file "Downloads/a.bin" holding "aaaaaaaa"
    And a file "Downloads/b.bin" holding "bbbbbbbb"
    When I look for duplicates
    Then "Downloads/a.bin" and "Downloads/b.bin" are not the same file

  Scenario: Only files that share a size are ever opened
    Given a file "Downloads/report.pdf" holding "quarterly numbers"
    And a file "Archive/report-final.pdf" holding "quarterly numbers"
    When I look for duplicates
    Then far fewer files were read than the survey holds

  Scenario: The original is kept and the copies are what can go
    Given a file "Downloads/report.pdf" holding "quarterly numbers"
    And a file "Archive/report-final.pdf" holding "quarterly numbers"
    When I look for duplicates
    Then the reclaimable copy is not the oldest one
    And what could be reclaimed is the size of one copy, not both

  Scenario: A copy hiding in a folder that needs review is still found
    Given a file "Downloads/report.pdf" holding "quarterly numbers"
    And a file "Documents/report-final.pdf" holding "quarterly numbers"
    When I look for duplicates
    Then "Downloads/report.pdf" and "Documents/report-final.pdf" are the same file

  Scenario: A copy inside a folder already going is not a second decision
    Given a file "Documents/report.pdf" holding "quarterly numbers"
    And a file "Downloads/old-build/report.pdf" holding "quarterly numbers"
    And "Documents/report.pdf" is the older of the two
    And "Downloads/old-build" has been judged to rebuild itself
    When I look for duplicates
    Then nothing inside "Downloads/old-build" is offered as a copy
    And "Documents/report.pdf" is not a duplicate of either

  Scenario: A version chain is reported as one decision
    Given a file "Downloads/NDA_v1.docx" holding "first draft"
    And a file "Downloads/NDA_v2.docx" holding "second draft"
    And a file "Downloads/NDA_v2_FINAL.docx" holding "second draft"
    When I look for duplicates
    Then "Downloads/NDA_v2.docx" and "Downloads/NDA_v2_FINAL.docx" are the same file
    And "Downloads/NDA_v1.docx" is not a duplicate of either
