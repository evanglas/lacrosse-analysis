# Parse the title row at the top of the page
def parse_team_legend(soup, school_id, team_id):
    legend = soup.fieldset.legend
    name = None
    athletics_href = None
    image_src = legend.img["src"]
    # Deal with potential for no link on team name
    possible_name = str(legend.img.next_sibling).strip()
    rpi_link = None
    if possible_name:
        name = possible_name
        rpi_link = legend.img.find_next_sibling("a")
    else:
        name_element = legend.img.next_sibling.next_sibling
        name = str(name_element.string).strip()
        athletics_href = name_element["href"]
        rpi_link = name_element.find_next_sibling("a")
    if "(" in name:
        name = name.split("(")[0].strip()
    rpi = None
    rpi_href = None
    if rpi_link:
        rpi = rpi_link.text.split()[-1]
        rpi_href = rpi_link["href"]
    return [[school_id, team_id, image_src, name, athletics_href, rpi, rpi_href]]


# Parse the venue information on the team page
def parse_venue(venue_div, school_id, team_id):
    labels = venue_div.find_all("label")

    name_label = venue_div.find(
        lambda x: x.name == "label" and x.string.strip() == "Name"
    )
    capacity_label = venue_div.find(
        lambda x: x.name == "label" and x.string.strip() == "Capacity"
    )
    year_built_label = venue_div.find(
        lambda x: x.name == "label" and x.string.strip() == "Year Built"
    )
    primary_venue_label = venue_div.find(
        lambda x: x.name == "label" and x.string.strip() == "Primary Venue"
    )

    name = name_label.next_sibling.strip()
    capacity = capacity_label.next_sibling.strip()
    year_built = year_built_label.next_sibling.strip()
    primary_venue = None

    if primary_venue_label:
        primary_venue = primary_venue_label.next_sibling.strip()

    return [school_id, team_id, name, capacity, year_built, primary_venue]


# Parse all venues on the team page
def parse_venues(soup, school_id, team_id):
    venues_div = soup.find("div", id="facility_div")
    if not venues_div:
        return None
    venues = []
    for venue_div in venues_div.find_all(
        lambda x: x.name == "div" and "team_page_season_venue" in x["id"]
    ):
        venues.append(parse_venue(venue_div, school_id, team_id))
    return venues


# Parse the head coach information on the team page
def parse_head_coach(head_coach_fieldset, school_id, team_id):
    fields = ["Alma mater", "Start date", "End date", "Seasons", "Record"]
    name_a = head_coach_fieldset.find("a")
    contents = [school_id, team_id, str(name_a.string).strip(), name_a["href"]]
    for field in fields:
        label = head_coach_fieldset.find(
            lambda x: x.name == "label" and field in str(x.string)
        )
        if label:
            contents.append(label.next_sibling.strip())
        else:
            contents.append(None)

    return contents


# Parse all coaches on the team page
def parse_head_coaches(soup, school_id, team_id):
    head_coaches_div = soup.find("div", id="head_coaches_div")
    if not head_coaches_div:
        return None
    head_coaches = []
    for fieldset in head_coaches_div.find_all("fieldset"):
        head_coaches.append(parse_head_coach(fieldset, school_id, team_id))
    return head_coaches


# Parse the record boxes on the team page, accepts the legend of the records general fieldset
def parse_records(soup, school_id, team_id):
    season_records_legend = soup.find(
        lambda x: x.name == "legend" and "Season-to-date" in str(x.string)
    )
    if not season_records_legend:
        return None

    record_fieldsets = season_records_legend.find_next_siblings("fieldset")
    record_rows = []

    for i, fieldset in enumerate(record_fieldsets):
        legend = fieldset.find("legend")
        legend_text = str(legend.string).strip()
        record_line = str(legend.next_sibling).strip().split()
        record = record_line[0]
        win_pct = re.sub(r"[()]", "", record_line[1])
        br = fieldset.find("br")
        streak_line = str(br.next_sibling).strip().split()
        streak = streak_line[1]
        record_rows.append([school_id, team_id, legend_text, record, win_pct, streak])

    return record_rows


# Parase the links on the team page
def parse_links(soup, school_id, team_id):
    roster_link = soup.find(lambda x: x.name == "a" and "Roster" in str(x.string))
    team_stats_link = soup.find(
        lambda x: x.name == "a" and "Team Statistics" in str(x.string)
    )
    game_by_game_link = soup.find(
        lambda x: x.name == "a" and "Game By Game" in str(x.string)
    )
    ranking_summary_link = soup.find(
        lambda x: x.name == "a" and "Ranking Summary" in str(x.string)
    )
    if (
        not roster_link
        and not team_stats_link
        and not game_by_game_link
        and not ranking_summary_link
    ):
        return None
    roster_href = roster_link["href"] if roster_link else None
    team_stats_href = team_stats_link["href"] if team_stats_link else None
    game_by_game_href = game_by_game_link["href"] if game_by_game_link else None
    ranking_summary_href = (
        ranking_summary_link["href"] if ranking_summary_link else None
    )

    return [
        [
            school_id,
            team_id,
            roster_href,
            team_stats_href,
            game_by_game_href,
            ranking_summary_href,
        ]
    ]


def parse_new_schedule(schedule_results_legend, school_id, team_id):
    schedule_table = schedule_results_legend.find_next_sibling("table")
    schedule_table_body = schedule_table.find("tbody")
    schedule_rows = []
    for tr in schedule_table_body.find_all("tr"):
        tds = tr.find_all("td")
        # skip border rows
        if len(tds) != 4:
            continue
        # Get details like "@" or stuff about championships
        before_details = str(tds[1].contents[0]).strip()
        after_details = str(tds[1].contents[-1]).strip()
        date = str(tds[0].string).strip()
        # Deal with no link on opponent
        opponent = None
        opponent_href = None
        opponent_img_src = None
        if tds[1].name == "a":
            opponent = str(tds[1].a.contents[-1]).strip()
            opponent_href = tds[1].a["href"]
            opponent_img_src = tds[1].a.img["src"]
        else:
            opponent_field = str(tds[1].string).strip()
            if len(opponent_field) > 0 and opponent_field[0] == "@":
                before_details = "@"
                after_details = ""
        result = None
        result_href = None
        if tds[2].a:
            result_href = tds[2].a["href"]
            result = str(tds[2].a.string).strip()
        elif tds[2].string:
            result = str(tds[2].string).strip()
        attendance = str(tds[3].string).strip()
        schedule_rows.append(
            [
                school_id,
                team_id,
                date,
                before_details,
                opponent,
                opponent_href,
                after_details,
                opponent_img_src,
                result,
                result_href,
                attendance,
            ]
        )
    return schedule_rows


def parse_old_schedule(schedule_result_td, school_id, team_id):
    heading = schedule_result_td.find_next("tr")
    schedule_rows = []
    for tr in heading.find_next_siblings("tr"):
        tds = tr.find_all("td")
        date = tds[0].string.strip()
        opponent_link = tds[1].a
        opponent_href = None
        opponent = None
        if opponent_link:
            opponent_href = opponent_link["href"]
            opponent = opponent_link.string.strip()
        else:
            opponent = tds[1].string.strip()
        result_link = tds[2].a
        result_href = None
        result = None
        if result_link:
            result_href = result_link["href"]
            result = result_link.string.strip()
        else:
            result = tds[2].string.strip()
        schedule_rows.append(
            [
                school_id,
                team_id,
                date,
                None,
                opponent,
                opponent_href,
                None,
                None,
                result,
                result_href,
                None,
            ]
        )
    return schedule_rows


# Parse team page schedule
def parse_schedule(soup, school_id, team_id):
    schedule_results_legend = soup.find(
        lambda x: x.name == "legend" and "Schedule/Results" in str(x.string)
    )
    if schedule_results_legend:
        return parse_new_schedule(schedule_results_legend, school_id, team_id)

    schedule_result_td = soup.find(
        lambda x: x.name == "td" and "Schedule/Results" in str(x.string)
    )

    if schedule_result_td:
        return parse_old_schedule(schedule_result_td, school_id, team_id)


def parse_team_stats(soup, school_id, team_id):
    team_stats_table = soup.find(
        lambda x: x.name == "table" and x.tbody and x.tbody.tr and x.tbody.tr
    )
    team_stats_table = soup.find("table", {"class": "mytable"})
    if not team_stats_table:
        return None
    team_stats_rows = []
    heading_tr = team_stats_table.find("tr", {"class": "heading"})
    if heading_tr.td and heading_tr.td.text.strip() == "Schedule/Results":
        return None
    for tr in team_stats_table.find_all("tr"):
        # skip header rows
        if tr.has_attr("class"):
            continue
        tds = tr.find_all("td")
        row_label = str(tds[0].a.string).strip()
        row_href = tds[0].a["href"]
        row_rank = str(tds[1].string).strip()
        row_value = str(tds[2].string).strip()
        team_stats_rows.append(
            [school_id, team_id, row_label, row_href, row_rank, row_value]
        )
    return team_stats_rows
