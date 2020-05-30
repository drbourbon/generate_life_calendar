import datetime
import argparse
import sys
import os
import cairo
import locale
import i18n
import io

DOC_WIDTH = 1872   # 26 inches
DOC_HEIGHT = 2880  # 40 inches
DOC_NAME = "life_calendar.pdf"

i18n.set('locale', 'it_IT')

i18n.add_translation('First week of the new year', 'Inizio anno', locale='it_IT')
i18n.add_translation('Week of your birthday', 'Compleanno', locale='it_IT')
i18n.add_translation('Weeks lived', 'Vissute', locale='it_IT')

XAXIS_DESC = "Settimane dell'anno"
YAXIS_DESC = "Anni di vita"

FONT = "Brocha"
BIGFONT_SIZE = 40
SMALLFONT_SIZE = 16
TINYFONT_SIZE = 14

MAX_TITLE_SIZE = 30
DEFAULT_TITLE = "CALENDARIO DELLA VITA"

NUM_ROWS = 88
NUM_COLUMNS = 52

Y_MARGIN = 144
BOX_MARGIN = 6

BOX_LINE_WIDTH = 3
BOX_SIZE = ((DOC_HEIGHT - (Y_MARGIN + 36)) / NUM_ROWS) - BOX_MARGIN
X_MARGIN = (DOC_WIDTH - ((BOX_SIZE + BOX_MARGIN) * NUM_COLUMNS)) / 2

LIVED_COLOUR = (0.88, 0.88, 0.88)
BIRTHDAY_COLOUR = (0.55, 0.55, 0.55)
NEWYEAR_COLOUR = (0.8, 0.8, 0.8)

ARROW_HEAD_LENGTH = 36
ARROW_HEAD_WIDTH = 8

def parse_date(date):
    formats = ['%d/%m/%Y', '%d-%m-%Y']
    stripped = date.strip()

    for f in formats:
        try:
            ret = datetime.datetime.strptime(date, f)
        except:
            continue
        else:
            return ret

    raise ValueError("Incorrect date format: must be dd-mm-yyyy or dd/mm/yyyy")

def draw_square(ctx, pos_x, pos_y, fillcolour=(1, 1, 1)):
    """
    Draws a square at pos_x,pos_y
    """

    ctx.set_line_width(BOX_LINE_WIDTH)
    ctx.set_source_rgb(0, 0, 0)
    ctx.move_to(pos_x, pos_y)

    ctx.rectangle(pos_x, pos_y, BOX_SIZE, BOX_SIZE)
    ctx.stroke_preserve()

    ctx.set_source_rgb(*fillcolour)
    ctx.fill()

def text_size(ctx, text):
    _, _, width, height, _, _ = ctx.text_extents(text)
    return width, height

def is_current_week(now, month, day):
    end = now + datetime.timedelta(weeks=1)
    date1 = datetime.datetime(now.year, month, day)
    date2 = datetime.datetime(now.year + 1, month, day)

    return (now <= date1 < end) or (now <= date2 < end)

def is_week_in_past(date):
    today = datetime.date.today()
    last_monday = today - datetime.timedelta(days=today.weekday())
    return date.date() < last_monday

def draw_row(ctx, pos_y, start_date, date, fill_lived):
    """
    Draws a row of 52 squares, starting at pos_y
    """

    pos_x = X_MARGIN

    for i in range(NUM_COLUMNS):
        fill=(1, 1, 1)

        if fill_lived and is_week_in_past(date):
            fill = LIVED_COLOUR
        elif is_current_week(date, start_date.month, start_date.day):
            fill = BIRTHDAY_COLOUR
        elif is_current_week(date, 1, 1):
            fill = NEWYEAR_COLOUR

        draw_square(ctx, pos_x, pos_y, fillcolour=fill)
        pos_x += BOX_SIZE + BOX_MARGIN
        date += datetime.timedelta(weeks=1)

def draw_key_item(ctx, pos_x, pos_y, desc, colour):
    draw_square(ctx, pos_x, pos_y, fillcolour=colour)
    pos_x += BOX_SIZE + (BOX_SIZE / 2)

    ctx.set_source_rgb(0, 0, 0)
    w, h = text_size(ctx, desc)
    ctx.move_to(pos_x, pos_y + (BOX_SIZE / 2) + (h / 2))
    ctx.show_text(desc)

    return pos_x + w + (BOX_SIZE * 2)

def draw_grid(ctx, date, years, fill_lived):
    """
    Draws the whole grid of 52x90 squares
    """
    start_date = date
    pos_x = X_MARGIN / 4
    pos_y = pos_x

    # Draw the key for box colours
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_NORMAL)

    pos_x = draw_key_item(ctx, pos_x, pos_y, i18n.t('Week of your birthday'), BIRTHDAY_COLOUR)
    pos_x = draw_key_item(ctx, pos_x, pos_y, i18n.t('First week of the new year'), NEWYEAR_COLOUR)
    draw_key_item(ctx, pos_x, pos_y, i18n.t('Weeks lived'), LIVED_COLOUR)

    # draw week numbers above top row
    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_NORMAL)

    pos_x = X_MARGIN
    pos_y = Y_MARGIN
    for i in range(NUM_COLUMNS):
        text = str(i + 1)
        w, h = text_size(ctx, text)
        ctx.move_to(pos_x + (BOX_SIZE / 2) - (w / 2), pos_y - BOX_SIZE)
        ctx.show_text(text)
        pos_x += BOX_SIZE + BOX_MARGIN

    ctx.set_font_size(TINYFONT_SIZE)
    ctx.select_font_face(FONT, cairo.FONT_SLANT_ITALIC,
        cairo.FONT_WEIGHT_NORMAL)

    for i in range(years):
        # Generate string for current date
        ctx.set_source_rgb(0, 0, 0)
        date_str = date.strftime('%d %b, %Y')
        w, h = text_size(ctx, date_str)

        # Draw it in front of the current row
        ctx.move_to(X_MARGIN - w - BOX_SIZE,
            pos_y + ((BOX_SIZE / 2) + (h / 2)))
        ctx.show_text(date_str)

        # Draw the current row
        draw_row(ctx, pos_y, start_date, date, fill_lived)

        # Increment y position and current date by 1 row/year
        pos_y += BOX_SIZE + BOX_MARGIN
        date += datetime.timedelta(weeks=52)

def gen_calendar(start_date, title, filename, years, fill_lived):
    if len(title) > MAX_TITLE_SIZE:
        raise ValueError("Title can't be longer than %d characters"
            % MAX_TITLE_SIZE)

    # Fill background with white
    out = io.BytesIO()
    surface = cairo.PDFSurface (out, DOC_WIDTH, DOC_HEIGHT)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(1, 1, 1)
    ctx.rectangle(0, 0, DOC_WIDTH, DOC_HEIGHT)
    ctx.fill()

    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
        cairo.FONT_WEIGHT_BOLD)
    ctx.set_source_rgb(0, 0, 0)
    ctx.set_font_size(BIGFONT_SIZE)
    w, h = text_size(ctx, title)
    ctx.move_to((DOC_WIDTH / 2) - (w / 2), (Y_MARGIN / 2) - (h / 2))
    ctx.show_text(title)

    # Back up to the last monday
    date = start_date
    while date.weekday() != 0:
        date -= datetime.timedelta(days=1)

    # Draw 52x90 grid of squares
    draw_grid(ctx, date, years, fill_lived)
    ctx.show_page()
    surface.finish()
    sys.stdout.buffer.write(out.getvalue())

def main():
    parser = argparse.ArgumentParser(description='\nGenerate a personalized "Life '
        ' Calendar", inspired by the calendar with the same name from the '
        'waitbutwhy.com store')

    parser.add_argument(type=str, dest='date', help='starting date; your birthday,'
        'in either dd/mm/yyyy or dd-mm-yyyy format')

    parser.add_argument('-f', '--filename', type=str, dest='filename',
        help='output filename', default=DOC_NAME)

    parser.add_argument('-s', '--stdout', action='store_true',
        help='dump PDF to standard output (for piping)')

    parser.add_argument('-t', '--title', type=str, dest='title',
        help='Calendar title text (default is "%s")' % DEFAULT_TITLE,
        default=DEFAULT_TITLE)


    parser.add_argument('-l', '--life-expectancy', type=int, dest='years',
        help='life expectancy in years, max 90, default 80', default=80)

    parser.add_argument('--locale', type=str, dest='locale',
        help='set locale for date and legenda generation', default='it_IT')

    parser.add_argument('-i', '--fill-lived', action="store_true", dest='fill_lived',
        help='fill lived weeks')

    args = parser.parse_args()

    locale.setlocale(locale.LC_TIME, args.locale)
    i18n.set('locale', args.locale)
    
    try:
        start_date = parse_date(args.date)
    except Exception as e:
        print("Error: %s" % e)
        return

    if (args.stdout):
        doc_name = None
    else:
        doc_name = '%s.pdf' % (os.path.splitext(args.filename)[0])

    years = max(1, min(88, args.years))

    try:
        gen_calendar(start_date, args.title, doc_name, years, args.fill_lived)
    except Exception as e:
        print("Error: %s" % e)
        return

#    print('Created %s' % doc_name)

if __name__ == "__main__":
    main()
