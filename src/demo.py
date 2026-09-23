"""Fictional fixtures only. Never derive demo output from uploaded audio."""

from datetime import date, timedelta

from src.schemas import ActionItem, MeetingSummary, Speaker, TranscriptSegment

DEMO_DATE = date(2026, 9, 23)
DEMO_NAMES = ["Айгерім", "Тимур", "Дана"]


def demo_speakers() -> list[Speaker]:
    return [Speaker(id=f"speaker_{index}", name=name) for index, name in enumerate(DEMO_NAMES, 1)]


def demo_transcript() -> list[TranscriptSegment]:
    rows = [
        (0, 12, "speaker_1", "ru", "Коллеги, обсуждаем пилот сервиса для местных магазинов. Нужно согласовать бюджет, презентацию и список клиентов."),
        (12, 25, "speaker_2", "kk", "Мен, Тимур, ертеңге дейін пилоттың бюджетін дайындаймын. Шығындарды жеке кестеге енгіземін."),
        (25, 39, "speaker_3", "mixed", "Мен, Дана, клиенттер тізімін дайындаймын и отправлю его через три дня. Для пилота выберем пять магазинов."),
        (39, 53, "speaker_1", "ru", "Я, Айгерім, подготовлю презентацию до 30 сентября 2026 года. Дана, свяжись с клиентами до 2 октября 2026 года."),
        (53, 65, "speaker_3", "kk", "Келістік, клиенттерге өзім хабарласамын. Пилотқа бес дүкен қатысады."),
        (65, 78, "speaker_2", "mixed", "Бюджет дайын болған соң обсудим расходы. Ещё нужно проверить договор; ответственного и срок пока не назначили."),
        (78, 90, "speaker_1", "kk", "Шешім қабылданды: пилотты бес дүкенмен бастаймыз. Келесі кездесуде бюджет пен нәтижелерді қараймыз."),
    ]
    return [TranscriptSegment(id=f"seg_{i}", start=start, end=end, speaker_id=speaker,
                              language=language, text=text)
            for i, (start, end, speaker, language, text) in enumerate(rows, 1)]


def demo_tasks(meeting_date: date) -> list[ActionItem]:
    return [
        ActionItem(assignee="Тимур", task="Подготовить бюджет пилота и таблицу расходов.",
                   deadline_original="ертеңге дейін", deadline_normalized=meeting_date + timedelta(days=1),
                   evidence_segment_ids=["seg_2"]),
        ActionItem(assignee="Дана", task="Подготовить и отправить список клиентов для пилота.",
                   deadline_original="через три дня", deadline_normalized=meeting_date + timedelta(days=3),
                   evidence_segment_ids=["seg_3"]),
        ActionItem(assignee="Айгерім", task="Подготовить презентацию.",
                   deadline_original="до 30 сентября 2026 года", deadline_normalized=date(2026, 9, 30),
                   evidence_segment_ids=["seg_4"]),
        ActionItem(assignee="Дана", task="Связаться с клиентами.",
                   deadline_original="до 2 октября 2026 года", deadline_normalized=date(2026, 10, 2),
                   evidence_segment_ids=["seg_4", "seg_5"]),
        ActionItem(task="Проверить договор.", evidence_segment_ids=["seg_6"]),
    ]


def demo_summary() -> MeetingSummary:
    return MeetingSummary(
        overview="Команда обсудила запуск пилота сервиса для пяти местных магазинов и распределила подготовительные задачи.",
        discussion_points=["Бюджет и учёт расходов.", "Список клиентов, презентация и контакты с магазинами.",
                           "Проверка договора: ответственный и срок ещё не определены."],
        decisions=["Пилотқа бес дүкен қатысады — в пилоте участвуют пять магазинов.",
                   "На следующей встрече рассмотреть бюджет и результаты."],
    )
