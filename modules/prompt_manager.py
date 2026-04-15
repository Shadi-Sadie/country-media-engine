from pathlib import Path
import re

from modules.un_schedule import format_week_tag, resolve_un_schedule


SCRIPT_TEMPLATE_PATH = Path("prompt.template.txt")
FUN_TEMPLATE_PATH = Path("prompt_fun.template.txt")
LINKS_TEMPLATE_PATH = Path("prompt_links.template.txt")


def _hashtag_token(text: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_]+", "", (text or "").replace(" ", "_"))
    return cleaned or "Country"


def _build_context(country: str, output_dir: str, week_number: int | None = None) -> dict[str, str]:
    entry = resolve_un_schedule(country=country, week_number=week_number)
    country = entry.country_name
    country_tag = _hashtag_token(country)
    hashtag_lines = "\n".join(
        [
            format_week_tag(entry.week_number),
            f"#{country_tag}",
            f"#{country[0].upper()}" if country and country[0].isalpha() else "",
            "@countries_AtoZ",
        ]
    ).replace("\n\n", "\n").strip()
    return {
        "country": country,
        "output_dir": output_dir,
        "wiki_filename": f"{country}_wiki.txt",
        "wiki_path": f"{output_dir}/{country}_wiki.txt",
        "script_filename": f"{country}_script.txt",
        "script_path": f"{output_dir}/{country}_script.txt",
        "fun_fact_filename": f"{country}_fun_fact.txt",
        "fun_fact_path": f"{output_dir}/{country}_fun_fact.txt",
        "links_filename": f"{country}_links.txt",
        "links_path": f"{output_dir}/{country}_links.txt",
        "hashtags_lines": hashtag_lines,
    }


def _render_template(template_path: Path, context: dict[str, str]) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    return template_path.read_text(encoding="utf-8").format(**context).strip() + "\n"


def prepare_country_prompts(
    country: str,
    output_dir: str = "outputs",
    week_number: int | None = None,
) -> dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    context = _build_context(country, output_dir, week_number=week_number)
    country = context["country"]
    script_prompt = _render_template(SCRIPT_TEMPLATE_PATH, context)
    fun_prompt = _render_template(FUN_TEMPLATE_PATH, context)
    links_prompt = _render_template(LINKS_TEMPLATE_PATH, context)

    generated_paths = {
        "root_script_prompt": Path("prompt.txt"),
        "root_fun_prompt": Path("prompt_fun.txt"),
        "legacy_fun_prompt": Path("prompt-fun.txt"),
        "root_links_prompt": Path("prompt_links.txt"),
        "legacy_root_links_format_prompt": Path("prompt_links_format.txt"),
        "output_script_prompt": out_dir / f"{country}_prompt.txt",
        "output_fun_prompt": out_dir / f"{country}_prompt_fun.txt",
        "output_links_prompt": out_dir / f"{country}_prompt_links.txt",
        "legacy_output_links_format_prompt": out_dir / f"{country}_prompt_links_format.txt",
    }

    generated_paths["root_script_prompt"].write_text(script_prompt, encoding="utf-8")
    generated_paths["root_fun_prompt"].write_text(fun_prompt, encoding="utf-8")
    generated_paths["legacy_fun_prompt"].write_text(fun_prompt, encoding="utf-8")
    generated_paths["root_links_prompt"].write_text(links_prompt, encoding="utf-8")
    generated_paths["legacy_root_links_format_prompt"].write_text(links_prompt, encoding="utf-8")
    generated_paths["output_script_prompt"].write_text(script_prompt, encoding="utf-8")
    generated_paths["output_fun_prompt"].write_text(fun_prompt, encoding="utf-8")
    generated_paths["output_links_prompt"].write_text(links_prompt, encoding="utf-8")
    generated_paths["legacy_output_links_format_prompt"].write_text(links_prompt, encoding="utf-8")

    for legacy_path in (
        Path("prompt_links_research.txt"),
        out_dir / f"{country}_prompt_links_research.txt",
    ):
        if legacy_path.exists():
            legacy_path.unlink()

    return {name: str(path) for name, path in generated_paths.items()}
