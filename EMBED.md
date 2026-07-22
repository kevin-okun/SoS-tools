# Embedding a tool

Each tool reports its own height to the host page, so an embedded iframe fits its
content at any width with no inner scrollbar. Paste this where the host site allows
custom HTML. This works on a normal website or web app; it does not work in a Substack
post, which strips iframes (there, link to the tool instead).

## New York / New Jersey

```html
<iframe id="sos-swell-window-ny"
  src="https://tools.scienceofsurfing.com/swell-window-ny/"
  title="Swell Window Explorer — New York & New Jersey"
  loading="lazy" scrolling="no"
  style="width:100%; max-width:1160px; height:1100px; border:1px solid #e6e2da; border-radius:12px; display:block;">
</iframe>
<script>
  window.addEventListener('message', function (e) {
    if (e.origin !== 'https://tools.scienceofsurfing.com') return;
    var d = e.data && e.data['sos-embed']; if (!d || !d.height) return;
    var f = document.getElementById('sos-' + d.tool); if (f) f.style.height = d.height + 'px';
  });
</script>
```

For the Southern California tool, use the same block with
`src=".../swell-window/"` and `id="sos-swell-window"`. One `<script>` handles any
number of embedded tools on the page.

## Breaking Wave

Same pattern, with `src=".../breaking-wave/"`, `id="sos-breaking-wave"`,
`title="Breaking Wave — spill, plunge, or surge"`, and a starting height of
`1050px` (the resize script takes over from there).

## Notes

- The iframe loads the hosted tool, so the Science of Surfing branding, footer credits,
  and links travel with it and update whenever you update the tool.
- Keep the `e.origin` check; it makes the resize messages trusted.
- At ~900 px wide or more the tool shows the two-panel layout; narrower, it stacks.
