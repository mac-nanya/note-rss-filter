# note RSS filter

`https://note.com/metakit/rss` から最新 1 件だけを取り出し、記事のタイトルとURLだけを持つRSSを作ります。

## ローカル実行

```bash
python3 filter_note_rss.py \
  https://note.com/metakit/rss \
  docs/metakit_note_short.rss
```

出力例:

```xml
<item>
  <title>Adobeの黄昏</title>
  <link>https://note.com/metakit/n/n6adae5caab85</link>
</item>
```

## GitHub Actions

`.github/workflows/update-rss.yml` が30分ごとにRSSを生成し、`docs/metakit_note_short.rss` をコミットします。手動実行もできます。

GitHub Pagesで公開する場合は、リポジトリの Settings から Pages を開き、Source を `Deploy from a branch`、Branch を `main`、Folder を `/docs` にします。

公開URLは次の形になります。

```text
https://<GitHubユーザー名>.github.io/<リポジトリ名>/metakit_note_short.rss
```
