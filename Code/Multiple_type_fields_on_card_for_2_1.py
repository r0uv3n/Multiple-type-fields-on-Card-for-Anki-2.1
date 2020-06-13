import re

from anki.utils import  stripHTML
from anki.lang import _
import html

from aqt.clayout import CardLayout
from aqt.reviewer import Reviewer


# ==== Reviewer ====
#we only have to wrap init, since we can overwrite the assignment


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
        typedTexts.push(typedTextNode.value);
    }
    return typedTexts;
}
</script>
"""

def myRevHtml(self):
    return old_revHtml(self)+myRevHtmlText

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
    for f in self.card.model()["flds"]:
        if f["name"] == fld:
            typeCorrect = self.card.note()[f["name"]]
            if clozeIdx:
                # narrow to cloze
                typeCorrect = self._contentForCloze(typeCorrect, clozeIdx)
            self.typeFont = f["font"]
            self.typeSize = f["size"]
            break
    if not typeCorrect:
        #append none, so AnsAnswer indices don't missmatch
        self.typeCorrect.append(None)
        if typeCorrect is None:
            if clozeIdx:
                warn = _(
                    """\
Please run Tools>Empty Cards"""
                )
            else:
                warn = _("Type answer: unknown field %s") % fld
            return re.sub(self.typeAnsPat, warn, buf)
        else:
            # empty field, remove type answer pattern
            return re.sub(self.typeAnsPat, "", buf)
    buf = re.sub(self.typeAnsPat, """
<center>
<input type=text id=typeans name=typetxt onkeypress="_typeAnsPress();"
    style="font-family: '%s'; font-size: %spx;">
</center>
""" % (self.typeFont, self.typeSize), buf, 1)
    self.typeCorrect.append(typeCorrect) 
    return self.typeAnsQuestionFilter(buf)

def myTypeAnsAnswerFilter(self, buf, i):
    if i >= len(self.typeCorrect):
        return re.sub(self.typeAnsPat, "", buf)
    origSize = len(buf)
    buf = buf.replace("<hr id=answer>", "")
    hadHR = len(buf) != origSize
    # munge correct value
    cor = self.mw.col.media.strip(self.typeCorrect[i])
    cor = re.sub("(\n|<br ?/?>|</?div>)+", " ", cor)
    cor = stripHTML(cor)
    # ensure we don't chomp multiple whitespace
    cor = cor.replace(" ", "&nbsp;")
    cor = html.unescape(cor)
    cor = cor.replace("\xa0", " ")
    cor = cor.strip()
    given = self.typedAnswer[i]
    # compare with typed answer
    res = self.correct(given, cor, showBad=False)
    # and update the type answer area
    def repl(match):
        # can't pass a string in directly, and can't use re.escape as it
        # escapes too much
        s = """
<span style="font-family: '%s'; font-size: %spx">%s</span>""" % (
            self.typeFont, 
            self.typeSize, 
            res
        )
        if hadHR:
            # a hack to ensure the q/a separator falls before the answer
            # comparison when user is using {{FrontSide}}
            s = "<hr id=answer>" + s
        return s
    buf = re.sub(self.typeAnsPat, repl, buf, 1)
    return self.typeAnsAnswerFilter(buf, i + 1)

def myGetTypedAnswer(self): 
    self.web.evalWithCallback(
        "_getTypedTexts()", self._onTypedAnswer)


def myOnTypedAnswer(self, val: None) -> None:
    self.typedAnswer = val or [""]*len(self.typeCorrect)
    self._showAnswer()

oldInit = Reviewer.__init__
Reviewer.__init__ = myInit
old_revHtml=Reviewer.revHtml
Reviewer.revHtml = myRevHtml
Reviewer.typeAnsFilter = myTypeAnsFilter
Reviewer.typeAnsQuestionFilter = myTypeAnsQuestionFilter
Reviewer.typeAnsAnswerFilter = myTypeAnsAnswerFilter
Reviewer._onTypedAnswer = myOnTypedAnswer
Reviewer._getTypedAnswer = myGetTypedAnswer


# ==== CLayout ====
def myMaybeTextInput(self, txt, type="q"):
    ret = oldMaybeTextInput(self, txt, type)
    if type == "q":
        ret = re.sub("id='typeans'", "id='typeans' name='typetxt'", ret)
    return ret

oldMaybeTextInput = CardLayout.maybeTextInput
CardLayout.maybeTextInput = myMaybeTextInput
