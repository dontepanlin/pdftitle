
from typing import Optional

from . import verbose

from pdfminer import utils
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdffont import PDFUnicodeNotDefined

class TextOnlyDevice(PDFDevice):

    def __init__(
            self, 
            rsrcmgr, 
            missing_char):
        PDFDevice.__init__(self, rsrcmgr)
        self.last_state = None
        # contains (font, font_size, string)
        self.blocks = []
        # current block
        # font, font size, glyph y, [chars]
        self.current_block = None
        # replacement missing_char
        self.missing_char = missing_char

    # at the end of the file, we need to recover last paragraph
    def recover_last_paragraph(self):
        if self.current_block is None:
            raise Exception("current block is None, this might be a bug. " +
                            "please report it together with the pdf file")
        if len(self.current_block[4]) > 0:
            self.blocks.append(self.current_block)

    # pdf spec, 5.3.3 text space details
    def new_tx(self, w, Tj, Tfs, Tc, Tw, Th):  # -pylint: disable=no-self-use,too-many-arguments
        return ((w - Tj / 1000) * Tfs + Tc + Tw) * Th

    # pdf spec, 5.3.3 text space details
    def new_ty(self, w, Tj, Tfs, Tc, Tw):  # -pylint: disable=no-self-use,too-many-arguments
        return (w - Tj / 1000) * Tfs + Tc + Tw

    def process_string(self, ts, array):
        verbose('SHOW STRING ts: ', ts)
        verbose('SHOW STRING array: ', array)
        for obj in array:
            verbose("processing obj: ", obj)
            # this comes from TJ, number translates Tm
            if utils.isnumber(obj):
                Tj = obj
                verbose("processing translation: ", Tj)
                # translating Tm, change tx, ty according to direction
                if ts.Tf.is_vertical():
                    tx = 0
                    ty = self.new_ty(0, Tj, ts.Tfs, 0, ts.Tw)
                else:
                    tx = self.new_tx(0, Tj, ts.Tfs, 0, ts.Tw, ts.Th)
                    ty = 0
                # update Tm accordingly
                ts.Tm = utils.translate_matrix(ts.Tm, (tx, ty))
                # there is an heuristic needed here, not sure what
                # if -Tj > ts.Tf.char_width('o'):
                #    self.draw_cid(ts, 0, force_space=True)
            else:
                verbose("processing string")
                for cid in ts.Tf.decode(obj):
                    self.draw_cid(ts, cid)

    # -pylint: disable=too-many-branches
    def draw_cid(self, ts, cid, force_space=False):
        verbose("drawing cid: ", cid)
        # see official PDF Reference 5.3.3 Text Space Details
        Trm = utils.mult_matrix(
            (ts.Tfs * ts.Th,    0,              # ,0
             0,                 ts.Tfs,         # ,0
             0,                 ts.Trise        # ,1
             ),
             ts.Tm)
        verbose('Trm', Trm)
        # note: before v0.10, Trm[1] and Trm[2] is checked to be 0
        # and if it is not, the character omitted (return from func)
        # this is correct if only translation Trm[4,5] and
        # scaling Trm[0,3] exists
        # but theoretically Trm[1,2] can also have values
        if cid == 32 or force_space:
            Tw = ts.Tw
        else:
            Tw = 0
        try:
            if force_space:
                unichar = ' '
            else:
                unichar = ts.Tf.to_unichr(cid)
        except PDFUnicodeNotDefined as unicode_not_defined:
            if self.missing_char:
                unichar = self.missing_char
            else:
                raise Exception("PDF contains a unicode char that does not " +
                                "exist in the font") from unicode_not_defined
        (gx, gy) = utils.apply_matrix_pt(Trm, (0, 0))
        verbose("drawing unichar: '", unichar, "' @", gx, ",", gy)
        tfs = Trm[0]
        if self.current_block is None:
            self.current_block = (ts.Tf, tfs, gx, gy, [unichar])
        elif ((self.current_block[0] == ts.Tf) and
              (self.current_block[1] == tfs)):
            self.current_block[4].append(unichar)
        else:
            self.blocks.append(self.current_block)
            self.current_block = (ts.Tf, tfs, gx, gy, [unichar])
        verbose('current block: ', self.current_block)
        verbose('blocks: ', self.blocks)
        if force_space:
            pass
        else:
            w = ts.Tf.char_width(cid)
            # below Tj is sent as zero because it is adjust in the caller
            if ts.Tf.is_vertical():
                tx = 0
                ty = self.new_ty(w, 0, ts.Tfs, ts.Tc, Tw)
            else:
                tx = self.new_tx(w, 0, ts.Tfs, ts.Tc, Tw, ts.Th)
                ty = 0
            ts.Tm = utils.translate_matrix(ts.Tm, (tx, ty))
