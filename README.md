# GREENWAKAME PLAYGROUND

PLAYGROUND WORKSは、greenwakameのゲームと実験作品を展示する、独立したオリジナル作品集です。初代PlayStation時代のゲーム文化から着想を得ています。特定のメーカーや公式シリーズとの関係はありません。

## 収録作品

PW / 001：Midnight Inspection（深夜巡回）。現在のPhase 1は、3Dの廊下を中心としたホラーの技術プロトタイプです。3室を巡回して異変を記録する操作、2種類のエンディング、音声の合成を実装しています。昭和の日本家屋を舞台にしたホラーへの発展は将来構想です。

## 構造

| パス | 用途 |
| --- | --- |
| `src/` | サイトのCSS・テンプレート・ジャケット・補足ライセンス原文 |
| `metadata/works.json` | 作品情報・操作・開発履歴・バージョンの登録 |
| `scripts/` | サイト生成・ローカル配信・静的検査・HTTP検証 |
| `site/` | GitHub Pagesへ配信する静的ファイル |

Phase 1の配布物は`site/works/midnight-inspection/v0.1.0-phase1/`に固定しています。`build-info.json`を含む13ファイルを変更・再ビルドしません。今後のバージョンは別ディレクトリに追加します。作品メタデータには外部サイトで動く作品のHTTPSリンクも登録できます。

## ローカル確認

Python 3.9以上と標準ライブラリを使用します。現在の確認環境はPython 3.9.6です。サイトの生成と配信にNodeやパッケージの追加インストールは不要です。

以下のコマンドはリポジトリのルートから実行します。生成処理はサイトの案内ページを更新し、固定版ゲームには書き込みません。

```sh
python3 -B scripts/build-site.py --update-portal
```

4183番のサーバーが正常に動いている場合は、そのサーバーを使います。動いていない場合は、次のコマンドで起動します。

```sh
python3 -B scripts/serve.py --port 4183
```

[トップページ](http://127.0.0.1:4183/greenwakame-playground/)から、作品一覧・作品紹介・ゲーム・ライセンスページへ進めます。ゲームは別タブで開き、開始ボタンを直接クリックします。ヘッドホンを推奨します。

サーバーを起動したまま、別のターミナルで検証します。検査結果はローカルの新規ファイルに保存します。既存の記録を上書きしないため、再検証時は両コマンドのファイル名をそろえて、未使用の名前に変えます。

```sh
python3 -B scripts/audit-site.py --report audit/public-inventory-review.json
python3 -B scripts/check-http.py --inventory audit/public-inventory-review.json --report audit/http-check-review.json
```

HTTP検証はローカル配信の専用検査です。ファイルの内容・ハッシュ・Content-Type、内部リンク、公開用サブパス、存在しないファイルの404応答を確認します。

ゲームの主な確認対象はmacOS Google Chromeです。過去のユーザー手動QAは8/8 PASSですが、そのChromeバージョンは未記録です。サイトデザインはユーザー承認済みです。この記録は、新たにゲームを再検証した結果ではありません。

## 公開方式

GitHub Pagesで`site/`のみを静的配信します。公開用baseは`/greenwakame-playground/`です。予定URLは[GREENWAKAME PLAYGROUND](https://greenwakame.github.io/greenwakame-playground/)です。現在はまだ公開していません。

`.github/workflows/pages.yml`はGitHub Actionsの手動起動（`workflow_dispatch`）専用です。pushやpull requestではデプロイしません。ゲームの再ビルドやパッケージのインストールも行いません。

公開承認後、GitHubリポジトリのSettings → Pagesで配信元をGitHub Actionsに設定します。リポジトリのActions権限と`github-pages` environmentのブランチ・承認条件を確認し、`main`を選んで手動実行します。ジョブは`main`以外では実行しません。公開URLはデプロイ結果から取得します。リポジトリ作成・commit・push・Pages設定・手動デプロイには別途承認が必要です。

構成は[GitHub Pagesの公式手順](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)に従っています。

## 権利とライセンス

自作コード・文章・デザイン・画像に、この展示による新しい再利用許諾は付与しません。第三者コードには各ライセンスが適用されます。AI生成のジャケットはコンセプトアートで、ゲームの実画面ではありません。

詳細は[RIGHTS.md](RIGHTS.md)、[ライセンスページ](site/licenses/index.html)、[補足ライセンス資料](site/licenses/supplement/index.html)を参照してください。

Phase P1-I-R1では、確認した再配布条件についてRELEASE READYと評価しています。残存18項目の評価はCOVERED 15 / ACTION REQUIRED 0 / EVIDENCE GAP 0 / NON-BLOCKING 3です。完全なCargo.lockと一部の依存解決バージョンは未確定です。保守的に収録した表示資料と評価範囲を補足ページに記録しており、完全なSBOMや法的保証を示すものではありません。固定版内の古い監査記録は、当時の履歴として保持しています。

`.gitignore`による除外だけで、秘密情報の公開防止を保証することはできません。初回コミット前に、明示した追加対象とステージ済みファイルを別途検査します。
