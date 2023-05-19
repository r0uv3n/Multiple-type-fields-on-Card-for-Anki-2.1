""" This module monkey patches the anki Reviewer to enable multiple type fields on cards. """

import re
from typing import Union, Callable, Match

from aqt.clayout import CardLayout
from aqt.reviewer import Reviewer
from aqt.utils import tr

# ==== Reviewer ====
# we only have to wrap init, since we can overwrite the assignment


def myInit(self, mw):
  oldInit(self, mw)
  self.typeCorrect = []


#This is only a constant attached to the reviewer which makes it easy to replace
myRevHtmlText = """
<script>
typetxts = document.getElementsByName("typetxt");
function _getTypedTexts(){
    typedTexts = [];
    for (let i = 0, typedTextNode; (typedTextNode = typetxts[i]); i++) {
        typedTexts.push(typedTextNode.value) ?? null;
    }
    return typedTexts;
}
</script>
"""


def myRevHtml(self):
  return old_revHtml(self) + myRevHtmlText


#Sadly we cannot use the original code in the functions below this
def myTypeAnsFilter(self, buf):
  if self.state == "question":
    self.typeCorrect = []
    return self.typeAnsQuestionFilter(buf)
  else:
    return self.typeAnsAnswerFilter(buf, 0)


def myTypeAnsQuestionFilter(self, buf):
  clozeIdx = None
  m = re.search(self.typeAnsPat, buf)
  if not m:
    return buf
  fld = m.group(1)
  # if it's a cloze, extract data
  if fld.startswith("cloze:"):
    # get field and cloze position
    clozeIdx = self.card.ord + 1
    fld = fld.split(":")[1]
  # loop through fields for a match
  for f in self.card.note_type()["flds"]:
    if f["name"] == fld:
      typeCorrect = self.card.note()[f["name"]]
      if clozeIdx:
        # narrow to cloze
        typeCorrect = self._contentForCloze(typeCorrect, clozeIdx)
      self.typeFont = f["font"]
      self.typeSize = f["size"]
      break
  if not typeCorrect:
    # append none, so AnsAnswer indices don't missmatch
    self.typeCorrect.append(None)
    if typeCorrect is None:
      if clozeIdx:
        warn = tr.studying_please_run_toolsempty_cards()
      else:
        warn = tr.studying_type_answer_unknown_field(val=fld)
      return re.sub(self.typeAnsPat, warn, buf)
    else:
      # empty field, remove type answer pattern
      return re.sub(self.typeAnsPat, "", buf, count=1)
  buf = re.sub(
      self.typeAnsPat, f"""
<center>
<input type=text id=typeans  name=typetxt onkeypress="_typeAnsPress();"
   style="font-family: '{self.typeFont}'; font-size: {self.typeSize}px;">
</center>
""", buf, count = 1
  )
  self.typeCorrect.append(typeCorrect)
  return self.typeAnsQuestionFilter(buf)


def myTypeAnsAnswerFilter(self, buf: str, i: int) -> str:
  if i >= len(self.typeCorrect):
    return re.sub(self.typeAnsPat, "", buf)
  origSize = len(buf)
  buf = buf.replace("<hr id=answer>", "")
  hadHR = len(buf) != origSize
  # munge correct value
  expected = self.typeCorrect[i]
  provided = self.typedAnswer[i]
  # compare with typed answer
  output = self.mw.col.compare_answer(expected, provided)

  # and update the type answer area
  def repl(match: Match) -> str:
    # can't pass a string in directly, and can't use re.escape as it
    # escapes too much
    s = """
<div style="font-family: '{}'; font-size: {}px">{}</div>""".format(
        self.typeFont,
        self.typeSize,
        output,
    )
    if hadHR:
      # a hack to ensure the q/a separator falls before the answer
      # comparison when user is using {{FrontSide}}
      s = f"<hr id=answer>{s}"
    return s

  buf = re.sub(self.typeAnsPat, repl, buf, count=1)
  return self.typeAnsAnswerFilter(buf, i + 1)


def myGetTypedAnswer(self):
  self.web.evalWithCallback("_getTypedTexts()", self._onTypedAnswer)


def myOnTypedAnswer(self, val: None) -> None:
  self.typedAnswer = val or [""] * len(self.typeCorrect)
  self._showAnswer()


oldInit = Reviewer.__init__
Reviewer.__init__ = myInit
old_revHtml = Reviewer.revHtml
Reviewer.revHtml = myRevHtml
Reviewer.typeAnsFilter = myTypeAnsFilter
Reviewer.typeAnsQuestionFilter = myTypeAnsQuestionFilter
Reviewer.typeAnsAnswerFilter = myTypeAnsAnswerFilter
Reviewer._onTypedAnswer = myOnTypedAnswer
Reviewer._getTypedAnswer = myGetTypedAnswer


# ==== CLayout ====
def myMaybeTextInput(self, txt: str, type: str = "q") -> str:
  if "[[type:" not in txt:
    return txt
  origLen = len(txt)
  txt = txt.replace("<hr id=answer>", "")
  hadHR = origLen != len(txt)

  def answerRepl(match: Match) -> str:
    res = self.mw.col.compare_answer("example", "sample")
    if hadHR:
      res = f"<hr id=answer>{res}"
    return res

  type_filter = r"\[\[type:.+?\]\]"
  repl: Union[str, Callable]

  if type == "q":
    repl = "<input id='typeans' name='typetxt' type=text value='example' readonly='readonly'>"
    repl = f"<center>{repl}</center>"
  else:
    repl = answerRepl
  out = re.sub(type_filter, repl, txt)

  return out


oldMaybeTextInput = CardLayout.maybeTextInput
CardLayout.maybeTextInput = myMaybeTextInput
