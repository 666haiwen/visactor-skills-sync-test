// Canvas measures text at render time: load the stylesheet and needed glyphs first.
if (schema.appearance?.typography?.fontFamily?.includes('Noto Serif SC')) {
  const fontUrl = 'https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&display=swap';
  const family = 'Noto Serif SC';
  document.getElementById('page').style.fontFamily = schema.appearance.typography.fontFamily;
  const textRuns = [];
  const collectText = value => {
    if (!value || typeof value !== 'object') return;
    if (value.type === 'text' && typeof value.text === 'string') textRuns.push(value.text);
    Object.values(value).forEach(collectText);
  };
  collectText(schema.body);
  const glyphs = [...new Set(textRuns.join(''))].join('') || '人物 Biography 0123456789';
  let timer;
  const link = document.createElement('link');
  link.rel = 'stylesheet'; link.href = fontUrl;
  try {
    const deadline = new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('字体 CDN 加载超时')), 20000);
    });
    const loading = (async () => {
      await new Promise((resolve, reject) => {
        link.onload = resolve;
        link.onerror = () => reject(new Error('字体 CDN 样式加载失败'));
        document.head.appendChild(link);
      });
      const results = await Promise.all([400, 700].map(async weight => {
        const faces = await document.fonts.load(`${weight} 24px "${family}"`, glyphs);
        if (!faces.length || faces.some(face => face.status !== 'loaded')) {
          throw new Error(`字体 ${weight} 未加载`);
        }
        return {family, weight: String(weight), status: 'loaded', source: fontUrl,
          matchedWeights: [...new Set(faces.map(face => face.weight))]};
      }));
      return results;
    })();
    window.__VINFO_FONTS__ = await Promise.race([loading, deadline]);
  } catch (error) {
    // Disable late CDN swaps so fallback measurement and final canvas stay consistent.
    link.remove();
    window.__VINFO_FONTS__ = [{family, status: 'fallback', source: fontUrl, reason: String(error)}];
    console.warn('使用系统宋体回退：', error);
  } finally {
    clearTimeout(timer);
  }
}
