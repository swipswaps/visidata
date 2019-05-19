import curses

from visidata import vd, VisiData, BaseSheet, Sheet, ColumnItem, Column, RowColorizer, CursesAttr, options, colors, wrmap, clipdraw


__all__ = ['StatusSheet', 'status']


@VisiData.global_api
def status(self, *args, priority=0):
    'Add status message to be shown until next action.'
    k = (priority, args)
    self.statuses[k] = self.statuses.get(k, 0) + 1

    if self.statusHistory:
        prevpri, prevargs, prevn = self.statusHistory[-1]
        if prevpri == priority and prevargs == args:
            self.statusHistory[-1][2] += 1
            return True

    self.statusHistory.append([priority, args, 1])
    return True


def middleTruncate(s, w):
    if len(s) <= w:
        return s
    return s[:w] + options.disp_truncator + s[-w:]


def composeStatus(msgparts, n):
    msg = '; '.join(wrmap(str, msgparts))
    if n > 1:
        msg = '[%sx] %s' % (n, msg)
    return msg


@BaseSheet.api
def leftStatus(sheet):
    'Compose left side of status bar for this sheet (overridable).'
    return options.disp_status_fmt.format(sheet=sheet, vd=vd)


@VisiData.api
def drawLeftStatus(vd, scr, vs):
    'Draw left side of status bar.'
    cattr = CursesAttr(colors.color_status)
    attr = cattr.attr
    error_attr = cattr.update_attr(colors.color_error, 1).attr
    warn_attr = cattr.update_attr(colors.color_warning, 2).attr
    sep = options.disp_status_sep

    x = 0
    y = vs.windowHeight-1  # status for each window
    try:
        lstatus = vs.leftStatus()
        maxwidth = options.disp_lstatus_max
        if maxwidth > 0:
            lstatus = middleTruncate(lstatus, maxwidth//2)

        x = clipdraw(scr, y, 0, lstatus, attr)

        vd.onMouse(scr, y, 0, 1, x,
                        BUTTON1_PRESSED='sheets',
                        BUTTON3_PRESSED='rename-sheet',
                        BUTTON3_CLICKED='rename-sheet')
    except Exception as e:
        vd.exceptionCaught(e)

    one = False
    for (pri, msgparts), n in sorted(vd.statuses.items(), key=lambda k: -k[0][0]):
        try:
            if x > vd.windowWidth:
                break
            if one:  # any messages already:
                x += clipdraw(scr, y, x, sep, attr, vd.windowWidth)
            one = True
            msg = composeStatus(msgparts, n)

            if pri == 3: msgattr = error_attr
            elif pri == 2: msgattr = warn_attr
            elif pri == 1: msgattr = warn_attr
            else: msgattr = attr
            x += clipdraw(scr, y, x, msg, msgattr, vd.windowWidth)
        except Exception as e:
            vd.exceptionCaught(e)


@VisiData.api
def rightStatus(vd, sheet):
    'Compose right side of status bar.'
    gerund = sheet.processing
    if gerund:
        status = '%9d  %2d%%%s' % (len(sheet), sheet.progressPct, gerund)
    else:
        status = '%9d %s' % (len(sheet), sheet.rowtype)
    return status, 'color_status'


@VisiData.api
def drawRightStatus(vd, scr, vs):
    'Draw right side of status bar.  Return length displayed.'
    rightx = vd.windowWidth-1

    ret = 0
    statcolors = [
        vd.checkMemoryUsage(),
        vd.rightStatus(vs),
        (vd.keystrokes, 'color_keystrokes'),
    ]

    if vd.cmdlog and vd.cmdlog.currentReplay:
        statcolors.insert(0, (vd.cmdlog.currentReplay.replayStatus, 'color_status_replay'))

    for rstatcolor in statcolors:
        if rstatcolor:
            try:
                rstatus, coloropt = rstatcolor
                rstatus = ' '+rstatus
                attr = colors.get_color(coloropt).attr
                statuslen = clipdraw(scr, vd.windowHeight-1, rightx, rstatus, attr, rtl=True)
                rightx -= statuslen
                ret += statuslen
            except Exception as e:
                vd.exceptionCaught(e)

    if scr:
        curses.doupdate()
    return ret


class StatusSheet(Sheet):
    precious = False
    rowtype = 'statuses'  # rowdef: (priority, args, nrepeats)
    columns = [
        ColumnItem('priority', 0, type=int, width=0),
        ColumnItem('nrepeats', 2, type=int, width=0),
        ColumnItem('args', 1, width=0),
        Column('message', getter=lambda col,row: composeStatus(row[1], row[2])),
    ]
    colorizers = [
        RowColorizer(1, 'color_error', lambda s,c,r,v: r and r[0] == 3),
        RowColorizer(1, 'color_warning', lambda s,c,r,v: r and r[0] in [1,2]),
    ]

    def reload(self):
        self.rows = vd.statusHistory[::-1]


BaseSheet.addCommand('^P', 'statuses', 'vd.push(StatusSheet("statusHistory"))')