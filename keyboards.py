from utils import B, kb
from i18n import t


def admin_kb(lang):
    return kb(
        [B(t("a_btn_drivers", lang), "a:drv"), B(t("a_btn_order", lang), "a:order")],
        [B(t("a_btn_orders", lang), "a:orders"), B(t("a_btn_stats", lang), "a:stats")],
        [B(t("a_btn_apps", lang), "a:apps"), B(t("a_btn_search", lang), "a:search")],
        [B(t("a_btn_bc", lang), "a:bc")],
        [B(t("btn_lang", lang), "lang")],
    )


def cancel_kb(lang):
    return kb([B(t("btn_cancel", lang), "home")])


def back_home(lang):
    return kb([B(t("btn_home", lang), "home")])
