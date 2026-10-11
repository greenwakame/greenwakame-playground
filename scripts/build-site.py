#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metadata-driven portal generator, Python 3.9+. Explicitly updates portal outputs; version distributions are immutable."""
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
import html
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
parser = argparse.ArgumentParser()
parser.add_argument("--update-portal", action="store_true", help="Update only generated portal pages, CSS and metadata")
args = parser.parse_args()
fixed = SITE / "works/midnight-inspection/v0.1.0-phase1"
fixed_before = {str(p.relative_to(fixed)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fixed.rglob("*") if p.is_file()}
assert len(fixed_before) == 13, "Fixed distribution inventory differs"
data = json.loads((ROOT / "metadata/works.json").read_text(encoding="utf-8"))
layout = (ROOT / "src/templates/layout.html").read_text(encoding="utf-8")
base = data["site"]["base"]
portfolio = data["site"]["portfolioUrl"]
works = data["works"]
assert base == "/greenwakame-playground/"
assert urlparse(portfolio).scheme == "https"
ids = set()
catalog_numbers = set()
for work in works:
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", work["id"])
    assert work["id"] not in ids
    ids.add(work["id"])
    assert work["kind"] in ("game", "experiment")
    assert isinstance(work["catalogNumber"], int) and work["catalogNumber"] > 0
    assert work["catalogNumber"] not in catalog_numbers, "Duplicate work number"
    catalog_numbers.add(work["catalogNumber"])
    assert isinstance(work["playable"], bool)
    cover = work["cover"]
    cover_path = PurePosixPath(cover["path"])
    assert not cover_path.is_absolute() and ".." not in cover_path.parts
    assert cover_path.parts[:2] == ("assets", "works") and cover_path.suffix == ".png"
    cover_source = ROOT / "src" / cover_path
    assert cover_source.resolve().is_relative_to((ROOT / "src/assets").resolve()) and not cover_source.is_symlink()
    assert cover["width"] == cover["height"] and cover["width"] > 0
    assert hashlib.sha256(cover_source.read_bytes()).hexdigest() == cover["sha256"]
    seen = set()
    for version in work["versions"]:
        assert version["id"] not in seen
        seen.add(version["id"])
        url = version["playUrl"]
        if version["hosting"] == "external":
            assert urlparse(url).scheme == "https" and urlparse(url).netloc
        else:
            assert version["hosting"] == "internal"
            assert not PurePosixPath(url).is_absolute() and ".." not in PurePosixPath(url).parts
            assert url.startswith("works/" + work["id"] + "/")
            assert (SITE / url / "index.html").is_file()

def esc(value):
    return html.escape(str(value), quote=True)

def link(path=""):
    return base + path

def play_url(version):
    if version["hosting"] == "external":
        return version["playUrl"]
    return link(version["playUrl"])

def chips(items):
    return '<div class="chips">' + "".join('<span class="chip">' + esc(item) + "</span>" for item in items) + "</div>"

def catalog(work):
    return "PW / " + str(work["catalogNumber"]).zfill(3)

def art(work):
    cover = work["cover"]
    return ('<div class="jacket"><img src="' + esc(link(cover["path"])) +
            '" width="' + str(cover["width"]) + '" height="' + str(cover["height"]) +
            '" alt="' + esc(cover["alt"]) + '" decoding="async"></div>')

def card(work):
    return ('<article class="work-card"><a class="card-link" href="' + link("works/" + work["id"] + "/") +
            '" aria-label="' + esc(catalog(work) + " " + work.get("japaneseTitle", work["title"]) + "の作品紹介") + '">' +
            art(work) + '<div class="card-copy"><div class="card-top"><span class="eyebrow">' + esc(catalog(work)) +
            '</span><span class="availability">' + ("試遊できます" if work["playable"] else "試遊準備中") + '</span></div>' +
            '<h3>' + esc(work.get("japaneseTitle", work["title"])) + '</h3><p class="english-title">' + esc(work["title"]) +
            '</p><p class="card-meta">' + esc(work["genre"]) + ' / ' + esc(work["stage"]) + '</p>' +
            '<p class="card-summary">' + esc(work["summary"]) + '</p><span class="card-cta">作品紹介・操作を見る <span aria-hidden="true">→</span></span>' +
            '<span class="cover-tag">ジャケット：AIコンセプトアート</span></div></a></article>')

def page(title, description, content, page_class=""):
    replacements = {"title": esc(title + " | GREENWAKAME PLAYGROUND"), "description": esc(description),
                    "base": base, "portfolio": esc(portfolio), "content": content, "page_class": esc(page_class)}
    output = layout
    for key, value in replacements.items():
        output = output.replace("{{" + key + "}}", value)
    assert "{{" not in output
    return output

def heading(label, title, intro, crumb=False):
    breadcrumb = '<p class="breadcrumb"><a href="' + base + '">Playground</a> / <a href="' + link("works/") + '">作品一覧</a></p>' if crumb else ""
    return '<div class="page-head">' + breadcrumb + '<p class="eyebrow">' + esc(label) + "</p><h1>" + esc(title) + '</h1><p class="intro">' + esc(intro) + "</p></div>"

outputs = {}
home = ('<section class="hero"><div><p class="eyebrow">ORIGINAL GAMES & EXPERIMENTS</p>'
        '<span class="archive-word" aria-hidden="true">PLAYGROUND</span><h1>小さなゲームと実験作品の展示室</h1>'
        '<p class="lead">greenwakameが制作したゲームと実験作品を展示しています。<br>ジャケットから作品を選び、内容と操作を確かめて試遊できます。</p></div>'
        '<aside class="hero-aside"><span class="hero-index">' + str(len(works)).zfill(2) + '</span><p class="eyebrow">PLAYGROUND WORKS</p>'
        '<p>PW / 001は「深夜巡回」。<br>3Dの廊下を巡回するホラーの技術プロトタイプです。</p>'
        '<span class="meta-line">公開準備中 · デザイン承認済み</span></aside></section>'
        '<section id="works" class="section"><div class="section-top"><div><span class="eyebrow">PLAYGROUND WORKS / CATALOG</span><h2>展示中の作品</h2></div>'
        '<a class="text-link" href="' + link("works/") + '">作品一覧を見る →</a></div>' + '<div class="work-grid">' + "".join(card(work) for work in works) + "</div></section>"
        '<section class="section"><p class="eyebrow">02 / ABOUT THE ARCHIVE</p><h2>試遊と制作の記録</h2><div class="grid3">'
        '<article class="note"><span class="num">PLAY</span><h3>ゲームを遊ぶ</h3><p>作品ごとに内容と基本操作を紹介しています。試遊ページは別タブで開きます。</p></article>'
        '<article class="note"><span class="num">EXPERIMENT</span><h3>実験作品</h3><p>ゲーム以外の表現やツールも今後追加する予定です。外部サイトで動く作品にも、このサイトから案内できる構成です。</p></article>'
        '<article class="note"><span class="num">PROCESS</span><h3>制作の記録</h3><p>使用技術と開発履歴を作品紹介にまとめています。過去のバージョンもたどれるように、完成時点の内容を保存します。</p></article></div></section>'
        '<section id="about" class="section"><div class="columns"><div><p class="eyebrow">03 / GREENWAKAME</p><h2>このサイトについて</h2></div><div>'
        '<p>Playgroundは、ゲームと実験作品を展示する独立したサイトです。CDゲームの売り場を着想源に、作品をジャケットと番号で紹介しています。今後も作品を追加し、制作の過程とともに紹介していきます。</p>'
        '<a class="text-link" href="' + esc(portfolio) + '">プロフィールとほかの制作物を見る ↗</a></div></div></section>')
outputs["index.html"] = page("ホーム", "greenwakameのゲーム・実験作品と制作過程を展示するPlayground。", home)
listing = heading("PLAYGROUND WORKS", "作品一覧", "展示中のゲームと、今後追加する実験作品を紹介します。")
for kind, title in (("game", "ゲーム"), ("experiment", "実験作品")):
    selected = [work for work in works if work["kind"] == kind]
    listing += '<section class="section"><div class="section-top"><h2>' + title + '</h2><span class="meta-line">' + str(len(selected)) + " WORK</span></div>"
    listing += ('<div class="work-grid">' + "".join(card(work) for work in selected) + "</div>") if selected else '<p class="empty">実験作品は今後追加する予定です。</p>'
    listing += "</section>"
outputs["works/index.html"] = page("作品一覧", "ゲームと実験作品の一覧。", listing)

for work in works:
    current = work["versions"][0]
    content = heading(data["site"]["label"] + " / " + catalog(work), work.get("japaneseTitle", work["title"]), work["title"], True)
    content += '<section class="work-hero"><figure class="cover-figure">' + art(work) + '<figcaption>' + esc(work["cover"]["caption"]) + '</figcaption></figure><div class="play-panel"><p class="eyebrow">' + esc(work["genre"]) + '</p><span class="status">' + esc(work["stage"]) + '</span><h2 style="margin-top:18px">' + esc(current["label"]) + "</h2><p>" + esc(work["description"]) + "</p>"
    content += '<a class="button" href="' + esc(play_url(current)) + '" target="_blank" rel="noopener">Phase 1を遊ぶ ↗</a><p class="small">別タブで開きます。ゲーム内の開始ボタンを直接クリックしてください。</p><p class="small">ヘッドホン推奨 · キーボード / マウス操作</p></div></section>'
    content += '<section class="section"><div class="columns"><div><p class="eyebrow">HOW TO PLAY</p><h2>基本操作</h2><table class="controls"><caption class="small" style="text-align:left">ゲーム中に使う操作</caption><tbody>'
    content += "".join('<tr><th scope="row">' + esc(keys) + "</th><td>" + esc(action) + "</td></tr>" for keys, action in work["controls"])
    content += '</tbody></table></div><div><p class="eyebrow">BEFORE YOU START</p><h2>遊ぶ前に</h2><ul>' + "".join("<li>" + esc(item) + "</li>" for item in work["requirements"]) + "</ul>"
    content += '<p>3室の確認札を調べ、扉の向こうの異変を確かめて記録します。巡回を終えたら、入口の報告ポストへ戻ってください。</p><p>Esc・タブ切替・フォーカス喪失で一時停止します。再開するには、ゲーム内の再開ボタンを直接クリックしてください。</p><p class="small">進捗の保存機能はありません。ページを再読み込みすると最初から始まります。</p></div></div></section>'
    if work.get("futurePlans"):
        content += '<section class="section"><p class="eyebrow">FUTURE CONCEPT</p><h2>今後の構想</h2><p>' + esc(work["futurePlans"]) + '</p></section>'
    content += '<section class="section"><div class="columns"><div><p class="eyebrow">TECH & PROCESS</p><h2>技術と制作過程</h2><p>Three.jsで廊下を描き、RapierのWASMで移動と衝突を処理します。環境音やノック、足音はWeb Audioで合成しています。</p>' + chips(work["technologies"]) + '</div><div><ol class="timeline">'
    content += "".join("<li><strong>" + esc(item["phase"]) + "</strong><p>" + esc(item["text"]) + "</p></li>" for item in work["history"])
    content += '</ol></div></div></section><section class="section"><p class="eyebrow">VERSION ARCHIVE</p><h2>バージョンと検証時点</h2>'
    for version in work["versions"]:
        details = ""
        if version["hosting"] == "internal":
            info = json.loads((SITE / version["playUrl"] / "build-info.json").read_text(encoding="utf-8"))
            details = '<p class="small">ソース記録：' + esc(info["sourceCommitRecordedAt"]) + "<br>公開用ビルド：" + esc(info["builtAt"]) + '<br>固定タグ：<code>' + esc(info["sourceTag"]) + "</code></p>"
        content += '<article class="version"><div><span class="eyebrow">' + esc(version["recordedAt"]) + " / " + ("EXTERNAL" if version["hosting"] == "external" else "PLAYGROUND") + "</span><h3>" + esc(version["label"]) + "</h3><code>" + esc(version["id"]) + "</code><p>" + esc(version["notes"]) + "</p>" + details + '</div><div class="actions"><a class="button secondary" href="' + esc(play_url(version)) + '" target="_blank" rel="noopener">このバージョンを遊ぶ ↗</a></div></article>'
    content += '<p class="small">Phase 1開発時のREADMEには、100テスト・Chrome手動QA 10/10のPASS記録があります。公開用ビルドも型検査・100テスト・ビルドがPASSしています。ユーザーによるmacOS Chrome手動QAは、過去に8/8 PASSと記録されています。Chromeバージョンは未記録です。サイトデザインはユーザー承認済みです。新しいバージョンは、同じ作品番号の開発履歴として別ディレクトリへ追加します。</p></section>'
    content += '<section class="section"><p class="eyebrow">CREDITS & LICENSES</p><h2>ライセンス</h2><div class="license-note"><p>Three.jsとRapierのライセンス本文を同梱しています。確認した表示条件への対応と不確実性は、補足ライセンス資料にまとめています。</p><a class="text-link" href="' + link("licenses/") + '">第三者ライセンスと確認状況を見る →</a></div><p class="small" style="margin-top:18px">自作部分には、この展示によって新たな再利用許諾を付与しません。第三者コードには各ライセンスが適用されます。</p></section>'
    outputs["works/" + work["id"] + "/index.html"] = page(work["title"], work["summary"], content, "midnight-page" if work["id"] == "midnight-inspection" else "work-page")

audit = json.loads((fixed / "LICENSE_AUDIT.json").read_text(encoding="utf-8"))
vbase = link("works/midnight-inspection/v0.1.0-phase1/")
content = heading("THIRD-PARTY LICENSES", "ライセンスと確認状況", "自作部分の利用条件と、第三者コードのライセンスを分けて表示しています。")
content += '<div class="prose"><div class="license-note"><strong>固定版作成時のライセンス記録</strong><p>以下の一覧は固定版作成時の記録です。最新の表示補完と条件の評価は、補足ライセンス資料をご覧ください。確認した再配布条件についてはRELEASE READYです。完全なCargo.lockと一部の依存解決バージョンは未確定です。GitHub Pagesではまだ公開していません。</p></div><h2>JavaScriptとランタイム</h2><ul><li>Three.js 0.186.1：MIT。著作権表示と本文を同梱。</li><li>Rapier 0.21.0：Apache-2.0。本文を同梱。インストール済みnpm配布物に独立したNOTICEは見当たりません。</li><li>Viteのmodulepreload補助コード：MIT。Vite本体のライセンスを追加同梱。</li></ul>'
content += '<p><a class="text-link" href="' + vbase + 'THIRD_PARTY_LICENSES.md">Viteが出力した第三者ライセンス全文</a></p><p><a class="text-link" href="' + vbase + 'VITE_RUNTIME_LICENSE.txt">ViteランタイムのMITライセンス</a></p>'
content += '<h2>WASM内部の依存</h2><p>配布WASMのパス文字列から10件のcrateとバージョンを確認しました。この方法だけでは、すべての依存を確認したことにはなりません。</p><div class="scroll-table"><table class="license-table"><thead><tr><th>依存</th><th>確認状況</th><th>本文</th></tr></thead><tbody>'
for item in audit["wasm"]["identifiedCrates"]:
    if item["status"] == "LICENSE_TEXTS_VERIFIED":
        status = "MIT OR Apache-2.0 / 同じバージョンの本文確認済み"
        refs = " · ".join('<a class="text-link" href="' + vbase + esc(entry["path"]) + '">' + esc(entry["path"].rsplit("/", 1)[-1]) + "</a>" for entry in item["files"])
    elif item["status"] == "MANIFEST_ONLY_HOLD":
        status, refs = "Apache-2.0の宣言を確認 / 表示要件はHOLD", "未完了"
    else:
        status, refs = "同じバージョンのライセンス・表示要件は未確認 / HOLD", "未完了"
    content += '<tr><th scope="row"><code>' + esc(item["crate"]) + "</code></th><td>" + esc(status) + "</td><td>" + refs + "</td></tr>"
content += '</tbody></table></div><h2>固定版作成時に残っていた確認</h2><ul><li>このWASMリリースに対応する、完全な依存一覧と有効機能。</li><li>未確認の依存に必要なライセンス本文、著作権表示、NOTICE。</li><li>Rust標準ライブラリ・コンパイラランタイムの扱い。</li></ul><p>Viteの自動一覧だけを、WASM内部まで含む完全な一覧とは扱いません。</p>'
content += '<p><a class="text-link" href="' + vbase + 'LICENSE_AUDIT.json">固定版作成時のライセンス監査記録</a> · <a class="text-link" href="' + vbase + 'build-info.json">固定版のビルド来歴</a></p><h2>自作部分</h2><p>自作のプログラム・文章・デザインについて、この展示によって新たな再利用許諾を付与しません。第三者コードにはそれぞれのライセンスが適用されます。</p><a class="text-link" href="' + link("rights/") + '">利用条件を見る →</a></div>'
outputs["licenses/index.html"] = page("ライセンス", "第三者ライセンス本文とWASM依存の監査状況。", content)
content = heading("TERMS", "利用条件", "自作部分と第三者コードの取り扱いについて。")
content += '<div class="prose"><h2>自作部分</h2><p>自作のプログラム、文章、デザインについて、この展示によって新たな再利用許諾を付与しません。</p><h2>第三者コード</h2><p>第三者コードには各権利者のライセンスが適用されます。これらの権利を、自作部分の方針で制限するものではありません。</p><a class="text-link" href="' + link("licenses/") + '">ライセンス本文と確認状況 →</a><h2>レビュー時点</h2><p>' + esc(data["site"]["reviewDate"]) + '。公開前のローカルレビュー用です。ユーザーによるmacOS Chrome手動QAは、過去に8/8 PASSと記録されています。Chromeバージョンは未記録です。サイトデザインはユーザー承認済みです。確認した再配布条件について、ライセンス監査はRELEASE READYです。完全なCargo.lockと一部の依存解決バージョンは未確定です。GitHub Pagesではまだ公開していません。</p></div>'
outputs["rights/index.html"] = page("利用条件", "自作部分と第三者コードの利用条件。", content)

# P1-G supplemental texts live outside the immutable game distribution.
supplement_source = ROOT / "src/license-supplement"
supplement_fragment = ROOT / "src/templates/license-supplement.html"
supplement_content = supplement_fragment.read_text(encoding="utf-8").replace("{{base}}", base)
outputs["licenses/supplement/index.html"] = page("補足ライセンス", "Phase 1の第三者ライセンスと確認した再配布条件。", supplement_content)
for source in sorted(supplement_source.rglob("*")):
    if source.is_file():
        assert not source.is_symlink()
        outputs["licenses/supplement/" + source.relative_to(supplement_source).as_posix()] = source.read_bytes()
supplement_notice = ('<div class="prose"><div class="license-note"><p>上記は固定版作成時の記録です。'
                     'その後に確認した表示の補完・ライセンス選択・未確認事項は、'
                     '<a class="text-link" href="' + link("licenses/supplement/") + '">補足ライセンス資料</a>をご覧ください。</p></div></div>')
outputs["licenses/index.html"] = outputs["licenses/index.html"].replace('</main>', supplement_notice + '</main>', 1)
outputs["404.html"] = page("ページが見つかりません", "指定のページが見つかりません。", heading("404", "ページが見つかりません。", "トップページから作品を選び直してください。") + '<div class="prose"><a class="button" href="' + base + '">Playgroundへ戻る →</a></div>')
outputs["assets/site.css"] = (ROOT / "src/site.css").read_text(encoding="utf-8")
for work in works:
    outputs[work["cover"]["path"]] = (ROOT / "src" / work["cover"]["path"]).read_bytes()
outputs["data/works.json"] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

# Validate all destinations before any write; only explicit portal updates are allowed.
pending = []
for name, content in outputs.items():
    path = SITE / name
    assert not any(version["id"] in path.parts for work in works for version in work["versions"]), "Version directory is immutable"
    assert path.resolve().is_relative_to(SITE.resolve()) and not path.is_symlink()
    payload = content.encode("utf-8") if isinstance(content, str) else content
    if path.exists():
        assert path.is_file(), "Destination is not a regular file: " + name
        if path.read_bytes() != payload:
            assert args.update_portal, "Use --update-portal to update generated portal files: " + name
            pending.append((path, payload, "wb"))
    else:
        pending.append((path, payload, "xb"))
for path, payload, mode in pending:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode) as stream:
        stream.write(payload)
fixed_after = {str(p.relative_to(fixed)): hashlib.sha256(p.read_bytes()).hexdigest() for p in fixed.rglob("*") if p.is_file()}
assert fixed_after == fixed_before, "Fixed distribution changed"
print("PORTAL PASS:", len(pending), "portal updates;", len(outputs), "total portal outputs; fixed version untouched")
