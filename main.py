###########################################################################
# Name: FontScaling
# Author: Shawn Alverson - SLAC National Accelerator Laboratory
# Largely based off of caQtDM from PSI: https://github.com/caqtdm/caqtdm
#
# Purpose: Proof-of-concept for bring dynamic font scaling to PyDM
###########################################################################

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument, QFontMetrics
from PyQt6.QtWidgets import QWidget, QLabel

# TODO: Test integration with PyDM Primitive Widget
# TODO: Test Widget border-width compensation
# TODO: Figure out way for widgets to enable/disable scaling at user's request (disabling stretch on layout will do this, but likely want QProperty?)
# TODO: Test for Vertical font labels.  Not sure if this is an option in PyDM currently?
# TODO: Get RichText support working (Qt.mightBeRichText() function not working in PyQt6 currently
# TODO: Optimize font point size calculation loops.  Can be laggy if resizing quickly or big changes
#        Ideas to do this:
#          - Figure out way to make rough initial prediction of pointSize to get close and then dial in from there
#          - Instead of constant 0.5 pointSize steps, adjust step size dynamically (start larger and get smaller as you approach desired size)
#          - Are all of the while loops actually necessary?  Could loops be combined or eliminated?
#          - 1000 loop iterations seems a bit much maybe?

# Global variables
FONT_SIZE_TOLERANCE_MARGIN = 3  # pixel
MIN_FONT_SIZE = 6


def longerThan(s1, s2):
    return s1.length() > s2.length()


# This function not actually needed?
def qasc(x):
    return x.toLatin1().constData()


# This class adapted largely from caQtDM (C++) and ported to Python.  This is where all of the font size calculations happen.
class FontScalingWidget(QWidget):
    def __init__(self, font_widget, parent=None):
        super(FontScalingWidget, self).__init__(parent)
        self.d_widget = font_widget
        self.d_scaleMode = 2  # caQtDM sets this to 0 by default, but that disables the scaling
        self.d_vertical = False
        self.d_lateralBorderWidth = 2
        self.d_botTopBorderWidth = 2
        self.d_fontScaleFactor = 1.0
        self.d_savedFont = self.d_widget.font()
        self.setFontScaleEnabled = True

    def setBotTopBorderWidth(self, pixValue):
        self.d_botTopBorderWidth = pixValue
        if self.d_scaleMode == 1 or self.d_scaleMode == 2:   # update
            self.rescaleFont(self.d_widget.text(), self.d_widget.size())  # calculateTextSpace())

    def setLateralBorderWidth(self, pixValue):
        self.d_lateralBorderWidth = pixValue
        if self.d_scaleMode == 1 or self.d_scaleMode == 2:  # update
            self.rescaleFont(self.d_widget.text(), self.d_widget.size())  # calculateTextSpace())

    def setScaleMode(self, mode):
        self.d_scaleMode = mode
        if mode == 1 or mode == 2:
            self.rescaleFont(self.d_widget.text(), self.d_widget.size())  # calculateTextSpace())
        else:
            # d_widget->setFont(d_savedFont); // no, let the designer do that
            pass

    def calculateFontPointSizeF(self, text, size):
        textDoc = QTextDocument()
        fmint = self.d_widget.fontMetrics()
        fm = QFontMetrics(fmint)
        f = self.d_widget.font()
        richText = False
        linecnt = text.count("\n") + 1

        # Do we have richtext?
        #if Qt.mightBeRichText(text):   # This Qt namespace function not working in PyQt6 yet (known issue)
        #    richText = True
        #    textDoc = QTextDocument()
        #    textCursor = QTextCursor(textDoc)
        #    textDoc.setDocumentMargin(0)
        #    textCursor.insertHtml(text)
        #    del textCursor

        if linecnt > 1:
            lines = text.split("\n")
            lines.sort(key=longerThan)
            longestLine = lines.first()
            txtHeight = fm.lineSpacing() * linecnt
        else:
            longestLine = text  # no newline
            txtHeight = fm.height()

        borderH1 = size.height() - self.d_botTopBorderWidth

        # scale according to width and height
        if self.d_scaleMode == 2:
            borderW1 = size.width() - self.d_lateralBorderWidth
            borderW2 = borderW1 - self.d_lateralBorderWidth

            # first scale according to height (same algorithm as below) and then verify width
            borderH2 = borderH1
            if txtHeight == (borderH1 + 1) or txtHeight == borderH1:
                # print(f'good: text for {widget().objectName()} :text "{text}" {txtHeight} | borderH1: {borderH1}] \
                # borderH2: {borderH2} pointSizeF {f.pointSizeF()}, h: {borderH1}\n')
                pass
            else:
                watchdog = 0
                while (txtHeight > borderH1 and f.pointSizeF() > MIN_FONT_SIZE) and (watchdog < 1000):
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(1.0)
                    else:
                        f.setPointSizeF(f.pointSizeF() - 0.5)
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()
                    watchdog += 1

                watchdog = 0
                while (txtHeight < borderH2) and (watchdog < 1000):
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(0.5)
                    else:
                        f.setPointSizeF(f.pointSizeF() + 0.5)
                    # print(f' ++ INCREASING font size for object "{qasc(self.d_widget.objectName())}" :text "{qasc(text)}" ' \
                    # 'height {txtHeight} - point size {f.pointSizeF()} - h: {borderH2}')
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()
                    watchdog += 1

            # check if width does not go outside - This will never be True currently.  See richtext commented block above
            if not richText:
                tmpFm = QFontMetrics(f)
                txtWidth = tmpFm.horizontalAdvance(longestLine)  # For PyQt5 use tmpFm.width(longestLine) instead
            else:
                textDoc.setDefaultFont(f)
                txtWidth = textDoc.idealWidth()

            watchdog = 0
            while (txtWidth > borderW2) and (f.pointSizeF() > MIN_FONT_SIZE) and (watchdog < 1000):
                if f.pointSizeF() <= 0.0:
                    f.setPointSizeF(1.0)
                f.setPointSizeF(f.pointSizeF() - 0.5)
                # print(f' \ -- next DECREASING font size "{qasc(self.d_widget.objectName())}" :text "{qasc(text)}" ' \
                # 'width {txtWidth} height {txtHeight} - point size {f.pointSizeF()} - w: {borderW2}')

                if not richText:
                    tmpFm = QFontMetrics(f)
                    txtWidth = tmpFm.horizontalAdvance(longestLine)  # For PyQt5 use tmpFm.width(longestLine) instead
                else:
                    textDoc.setDefaultFont(f)
                    txtWidth = textDoc.idealWidth()

                watchdog += 1

        # scale according to height only
        else:
            borderH2 = borderH1
            if txtHeight == (borderH1 + 1) or txtHeight == borderH1:
                # if (txtHeight == borderH1) {
                # print("good: text h %.2f\e[0m | borderH1: %.2f borderH2: %.2f pointSizeF %.2f, h: %.2f\n",
                # txtHeight, borderH1, borderH2, f.pointSizeF(), borderH1 );
                pass
            else:
                watchdog = 0
                while ((txtHeight > borderH1) and f.pointSizeF() > MIN_FONT_SIZE) and (watchdog < 1000):
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(1.0)
                    else:
                        f.setPointSizeF(f.pointSizeF() - 0.5)
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()
                    watchdog += 1

                watchdog = 0
                while (txtHeight < borderH2) and (watchdog < 1000):
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(0.5)
                    else:
                        f.setPointSizeF(f.pointSizeF() + 0.5)
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()
                    watchdog += 1

        if richText:
            del textDoc
        return f.pointSizeF()

    def calculateVertFontPointSizeF(self, text, size):
        fmint = self.d_widget.fontMetrics()
        fm = QFontMetrics(fmint)
        f = self.d_widget.font()
        linecnt = text.count("\n") + 1

        if linecnt > 1:
            lines = text.split("\n")
            lines.sort(key=longerThan)
            longestLine = lines.first()
            txtHeight = fm.lineSpacing() * linecnt
        else:
            longestLine = text  # no newline
            txtHeight = fm.height()

        borderH1 = size.height() - self.d_botTopBorderWidth
        borderH2 = borderH1
        borderW1 = size.width() - self.d_lateralBorderWidth
        borderW2 = borderW1 - self.d_lateralBorderWidth

        # scale according to width and height
        if self.d_scaleMode == 2:
            # first scale according to height (same algorithme as below) and then verify width * /
            if txtHeight == (borderW1 + 1) or txtHeight == borderW1:
                # printf("good: text for <%s> :text \"%s\" %.2f\e[0m | borderH1: %.2f borderH2: %.2f pointSizeF %.2f, h: %.2f\n",
                # qasc(widget()->objectName()), qasc(text), txtHeight, borderH1, borderH2, f.pointSizeF(), borderH1 );
                pass
            else:
                while (txtHeight > borderW1) and f.pointSizeF() > MIN_FONT_SIZE:
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(1.0)
                    else:
                        f.setPointSizeF(f.pointSizeF() - 0.5)
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()

                while txtHeight < borderW2:
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(0.5)
                    else:
                        f.setPointSizeF(f.pointSizeF() + 0.5)
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()

            # check if width does not go outside
            tmpFm = QFontMetrics(f)
            txtWidth = tmpFm.horizontalAdvance(longestLine)  # For PyQt5 use tmpFm.width(longestLine) instead
            while (txtWidth > borderH2) and f.pointSizeF() > MIN_FONT_SIZE:
                if f.pointSizeF() <= 0.0:
                    f.setPointSizeF(1.0)
                else:
                    f.setPointSizeF(f.pointSizeF() - 0.5)
                tmpFm = QFontMetrics(f)
                txtWidth = tmpFm.horizontalAdvance(longestLine)  # For PyQt5 use tmpFm.width(longestLine) instead
                # txtHeight = linecnt * tmpFm.lineSpacing();

        # scale according to height only
        else:
            if txtHeight == (borderW1 + 1) or txtHeight == borderW1:
                # printf("good: text h %.2f\e[0m | borderH1: %.2f borderH2: %.2f pointSizeF %.2f, h: %.2f\n",
                # txtHeight, borderH1, borderH2, f.pointSizeF(), borderH1 );
                pass
            else:
                while (txtHeight > borderW1) and f.pointSizeF() > MIN_FONT_SIZE:
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(1.0)
                    else:
                        f.setPointSizeF(f.pointSizeF() - 0.5)
                    # printf(" \e[1;36m -- DECREASING font size \"%s\" :text \"%s\"  height %.1f - point size %.2f - h: %.2f\e[0m\n",
                    # qasc(widget()->objectName()), qasc(text), txtHeight, f.pointSizeF(), borderH1);
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()

                while txtHeight < borderW2:
                    if f.pointSizeF() <= 0.0:
                        f.setPointSizeF(0.5)
                    else:
                        f.setPointSizeF(f.pointSizeF() + 0.5)
                    # printf(" \e[1;35m ++ INCREASING font size \"%s\" :text \"%s\" height %.1f - point size %.2f - h: %.2f\e[0m\n",
                    # qasc(widget()->objectName()), qasc(text), txtHeight, f.pointSizeF(), borderH2);
                    tmpFm = QFontMetrics(f)
                    txtHeight = linecnt * tmpFm.lineSpacing()

        return f.pointSizeF()

    def rescaleFont(self, text, size):
        if self.d_scaleMode != 1 and self.d_scaleMode != 2:
            return

        if self.d_vertical:
            fontSize = self.calculateVertFontPointSizeF(text, size)
        else:
            fontSize = self.calculateFontPointSizeF(text, size)

        if fontSize < MIN_FONT_SIZE:
            fontSize = MIN_FONT_SIZE

        f = self.d_widget.font()
        f.setPointSizeF(fontSize)
        self.d_widget.setFont(f)
        # print(f)


# Example class of regular Qt Widget using FontScalingWidget as a callable class
class ScalingLabel(QLabel):
    def __init__(self, text='', parent=None):
        # from PyQt6.QtWidgets import QSizePolicy

        super(ScalingLabel, self).__init__(text, parent)
        self.scaler = FontScalingWidget(self)
        # self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)  # Become QSizePolicy.Preferred in PyQt5
        # self.setMinimumSize(200, 25)
        # self.setMinimumHeight(25)
        # print(self.minimumSize().width(), self.minimumSize().height())

    def resizeEvent(self, e):
        self.scaler.rescaleFont(self.text(), self.size())
        super(ScalingLabel, self).resizeEvent(e)
        # print(self.minimumSize().width(), self.minimumSize().height())


# Example of a top-level inheritable widget class (comparable to PyDMPrimitiveWidget)
# TODO: Add QTimer to resizeEvent to slow down how often its called
# TODO: Add check for resize delta and only scale fonts if delta big enough (if (e.size() - e.oldSize) > MIN_DELTA)
# TODO: Investigate making this QMainWindow event rather than just parent widget class?
# TODO: Would it help performance to not create FontScalingWidget each Event for every child widget?
#       Try rewriting font scaler class such that its instantiated once for Parent widget and child is passed as argument to methods
class ScalingParentWidget(QWidget):
    def __init__(self, parent=None):
        super(ScalingParentWidget, self).__init__(parent)

    def resizeEvent(self, e):
        if self.children():
            for child in self.children():
                if issubclass(type(child), QWidget) and hasattr(child, 'text'):
                    font_scaler = FontScalingWidget(child)
                    font_scaler.rescaleFont(child.text(), child.size())
        else:
            font_scaler = FontScalingWidget(self)
            font_scaler.rescaleFont(self.text(), self.size())
        super(ScalingParentWidget, self).resizeEvent(e)


# Example of a simple widget using multiple-inheritance (comparable to PyDMLabel)
class SimpleWidget(QLabel, ScalingParentWidget):
    def __init__(self, text, parent=None):
        # from PyQt6.QtWidgets import QSizePolicy
        QLabel.__init__(self, parent)
        ScalingParentWidget.__init__(self, parent)

        self.setText(text)
        # self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Become QSizePolicy.Expanding in PyQt5


# Example of a compound widget using multiple child widgets
# TODO: QLineEdit may need special treatment. Do you really want font to resize based on how much text someone typed in?
# TODO: Should CompoundWidget children scale fonts independently, or somehow force all fonts to match the tightest constraint for uniformity?
class CompoundWidget(ScalingParentWidget):
    def __init__(self, label1, label2, parent=None):
        from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QSizePolicy
        super(CompoundWidget, self).__init__(parent)

        label = QLabel(label1)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Become QSizePolicy.Expanding in PyQt5
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)  # Become Qt.AlignRight in PyQt5
        edit = QLineEdit(label2)
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Become QSizePolicy.Expanding in PyQt5

        layout = QHBoxLayout()
        layout.addWidget(label, Qt.AlignmentFlag.AlignRight)  # Become Qt.AlignRight in PyQt5
        layout.addWidget(edit, Qt.AlignmentFlag.AlignLeft)    # Become Qt.AlignLeft in PyQt5

        # Setting all resizing font widgets to equal stretch value important for even, predictable scaling
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

        self.setLayout(layout)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout
    from sys import argv

    app = QApplication(argv)
    win = QMainWindow()

    widget = QWidget()
    normal_label = QLabel('Without Scaling')
    long_scaled_label = ScalingLabel('This is a long scaled label!')
    short_scaled_label = ScalingLabel('Shrt scld lbl!')
    compound_inherited_widget = CompoundWidget('QLabel:', 'this is a QLineEdit')
    simple_inherited_widget = SimpleWidget('Simple Scaling QLabel')

    layout = QVBoxLayout()
    layout.addWidget(normal_label)
    layout.addWidget(long_scaled_label)
    layout.addWidget(short_scaled_label)
    layout.addWidget(compound_inherited_widget)
    layout.addWidget(simple_inherited_widget)

    # These stretch factors seem to be necessary to reign in warring widget stretch - makes font scaling more predictable and even
    layout.setStretch(0, 1)
    layout.setStretch(1, 1)
    layout.setStretch(2, 1)
    layout.setStretch(3, 1)
    layout.setStretch(4, 1)

    widget.setLayout(layout)

    win.setCentralWidget(widget)
    win.show()

    exit(app.exec())
