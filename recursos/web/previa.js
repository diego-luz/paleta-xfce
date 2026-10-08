// Previa da area de trabalho e da tela de login, desenhada com as opcoes
// marcadas na pagina (antes de aplicar), e a galeria do fundo do login com o
// botao de escolher uma imagem. As cores repetem as do projeto.py.
"use strict";

const Previa = (() => {
  // paleta/modo -> fundo e texto (PALETAS) e a amostra das janelas (AMOSTRA:
  // janela, barra de titulo, texto, lateral, destaque, borda)
  const FUNDO = {
    nord: {escuro: ["#2E3440", "#D8DEE9"], claro: ["#ECEFF4", "#2E3440"]},
    gruvbox: {escuro: ["#282828", "#EBDBB2"], claro: ["#FBF1C7", "#3C3836"]},
    everforest: {escuro: ["#2D353B", "#D3C6AA"], claro: ["#FDF6E3", "#5C6A72"]},
  };
  const AMOSTRA = {
    "nord/escuro": ["#242933", "#2e3440", "#d8dee9", "#262b36", "#88c0d0", "#3b4252"],
    "nord/claro": ["#eceff4", "#e5e9f0", "#2e3440", "#e5e9f0", "#5e81ac", "#d8dee9"],
    "gruvbox/escuro": ["#282828", "#32302f", "#ebdbb2", "#3c3836", "#d79921", "#504945"],
    "gruvbox/claro": ["#fbf1c7", "#ebdbb2", "#3c3836", "#f2e5bc", "#b57614", "#d5c4a1"],
    "everforest/escuro": ["#2d353b", "#343f44", "#d3c6aa", "#343f44", "#a7c080", "#4f585e"],
    "everforest/claro": ["#fdf6e3", "#f4f0d9", "#5c6a72", "#f4f0d9", "#8da101", "#e0dcc7"],
  };
  const CORES_DOCK = ["#d4a85a", "#5e81ac", "#bf616a", "#a3be8c", "#b48ead", "#8fbcbb"];

  // a mesma conta do projeto.py, para o degrade e a barra sairem da paleta
  function misturar(a, b, quanto){
    const ca = [1, 3, 5].map(i => parseInt(a.slice(i, i + 2), 16));
    const cb = [1, 3, 5].map(i => parseInt(b.slice(i, i + 2), 16));
    return "#" + ca.map((x, i) => Math.round(x + (cb[i] - x) * quanto).toString(16).padStart(2, "0")).join("");
  }
  function textoSobre(cor){
    const [r, g, b] = [1, 3, 5].map(i => parseInt(cor.slice(i, i + 2), 16));
    return 0.299 * r + 0.587 * g + 0.114 * b > 150 ? "#1d1d1d" : "#ffffff";
  }
  function cores(e){
    const paleta = FUNDO[e.paleta] ? e.paleta : "nord";
    const modo = e.modo === "claro" ? "claro" : "escuro";
    const [fundo, texto] = FUNDO[paleta][modo];
    const [janela, titulo, textoJanela, lado, destaque, borda] = AMOSTRA[`${paleta}/${modo}`];
    const barra = misturar(fundo, modo === "escuro" ? "#000000" : "#ffffff", 0.22);
    return {fundo, texto, janela, titulo, textoJanela, lado, destaque, borda, barra,
            ilha: misturar(fundo, texto, modo === "escuro" ? 0.16 : 0.10),
            papelCima: misturar(fundo, texto, 0.14), papelBaixo: fundo};
  }

  let versaoPropria = 0;
  const faltam = new Set();
  const el = (tag, classe, texto) => {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  };
  const agora = new Date();
  const hora = agora.toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"});
  const RELOGIO = {
    curto: `${agora.toLocaleDateString("pt-BR", {weekday: "short", day: "2-digit", month: "short"})}  ${hora}`,
    completo: `${agora.toLocaleDateString("pt-BR", {weekday: "short", day: "2-digit", month: "long", year: "numeric"})}  ${hora}`,
    so_hora: hora,
  };

  // o fundo de cada escolha: o degrade ou a cor lisa da paleta, ou uma imagem
  // da pessoa, que vem em miniatura pela API (e pode nao existir)
  function fundoDoPapel(e){
    const c = cores(e);
    if (e.papel === "manter") return {url: "/api/papel-atual.jpg", texto: "papel de parede atual"};
    if (e.papel === "liso") return {css: c.papelCima};
    return {css: `linear-gradient(${c.papelCima}, ${c.papelBaixo})`};
  }
  function fundoDoLogin(e){
    if (e.login_fundo === "propria")
      return {url: `/api/login-propria.jpg?v=${versaoPropria}`, texto: "escolha uma imagem nos ajustes"};
    return fundoDoPapel(e);
  }
  function pintar(caixa, f){
    const sem = () => {
      caixa.style.background = "";
      caixa.classList.add("sem-imagem");
      caixa.dataset.texto = f.texto || "";
    };
    caixa.classList.remove("sem-imagem");
    if (f.css){ caixa.style.background = f.css; return; }
    if (!f.url || faltam.has(f.url)) return sem();
    caixa.style.background = `#2a2a2a url("${f.url}") center/cover no-repeat`;
    const prova = new Image();
    prova.onerror = () => { faltam.add(f.url); sem(); };
    prova.src = f.url;
  }

  // ---- area de trabalho ---------------------------------------------------
  function menu(e){
    if (e.menu === "nenhum") return null;
    const m = el("span", "pv-menu");
    m.appendChild(el("i"));
    if (e.menu === "icone_texto") m.appendChild(el("span", "", "Aplicativos"));
    return m;
  }
  function tarefas(e, ilha){
    if (e.barra_tarefas === "nenhuma") return null;
    const t = el("span", "pv-tarefas" + (e.barra_tarefas === "botoes" ? " botoes" : ""));
    if (e.barra_tarefas === "botoes"){
      ["Arquivos", "Terminal"].forEach((n, i) => t.appendChild(el("span", "pv-botao" + (i === 0 ? " ativo" : ""), n)));
    } else {
      CORES_DOCK.slice(0, ilha ? 6 : 5).forEach((cor, i) => {
        const b = el("i" , i === 0 ? "ativo" : ""); b.style.background = cor; t.appendChild(b);
      });
    }
    return t;
  }
  const bandeja = () => el("span", "pv-bandeja", "◦ ◦ ◦");

  function desktop(e){
    const c = cores(e);
    const tela = el("div", "pv-tela");
    tela.style.setProperty("--pv-acento", c.destaque);
    tela.style.setProperty("--pv-texto", c.texto);
    tela.style.setProperty("--pv-barra", c.barra);
    tela.style.setProperty("--pv-ilha", c.ilha);
    pintar(tela, fundoDoPapel(e));

    if (e.icones_area === "tudo" || e.icones_area === "so_removiveis"){
      const icones = el("div", "pv-icones-area");
      const nomes = e.icones_area === "tudo" ? ["Pasta pessoal", "Lixeira", "Pendrive"] : ["Pendrive"];
      nomes.forEach(n => { const i = el("span", "pv-icone-area"); i.append(el("i"), el("span", "", n)); icones.appendChild(i); });
      tela.appendChild(icones);
    }

    const relogio = el("span", "pv-hora", RELOGIO[e.relogio] || RELOGIO.curto);
    if (e.barra === "ilhas"){
      const topo = el("div", "pv-topo");
      [menu(e), el("span", "pv-esp"), bandeja(), relogio].forEach(x => x && topo.appendChild(x));
      tela.appendChild(topo);
      const t = tarefas(e, true);
      if (t){ const ilha = el("div", "pv-ilha"); ilha.appendChild(t); tela.appendChild(ilha); }
      tela.classList.add("ilhas");
    } else {
      const barra = el("div", "pv-barra " + (e.barra === "baixo" ? "baixo" : "topo"));
      [menu(e), tarefas(e, false), el("span", "pv-esp"), bandeja(), relogio].forEach(x => x && barra.appendChild(x));
      tela.appendChild(barra);
      tela.classList.add(e.barra === "baixo" ? "barra-baixo" : "barra-topo");
    }

    // uma janela de arquivos com as cores do tema da paleta
    const jan = el("div", "pv-janela" + (e.compacto === "nao" ? "" : " compacta"));
    jan.style.background = c.janela;
    jan.style.color = c.textoJanela;
    jan.style.borderColor = c.borda;
    const tit = el("div", "pv-tit");
    tit.style.background = c.titulo;
    tit.append(el("span", "", "Arquivos"), el("span", "pv-botoes", "–  ▢  ✕"));
    const corpo = el("div", "pv-corpo");
    const lado = el("div", "pv-lado");
    lado.style.background = c.lado;
    ["Pasta pessoal", "Documentos", "Imagens", "Downloads"].forEach((n, i) =>
      lado.appendChild(el("div", "pv-item" + (i === 2 ? " sel" : ""), n)));
    const area = el("div", "pv-area");
    for (let i = 0; i < 4; i++){
      const l = el("i"); l.style.background = c.borda; l.style.width = (90 - i * 14) + "%"; area.appendChild(l);
    }
    const bt = el("span", "pv-bt", "Abrir");
    bt.style.color = textoSobre(c.destaque);
    area.appendChild(bt);
    corpo.append(lado, area);
    jan.append(tit, corpo);
    tela.appendChild(jan);
    return tela;
  }

  // ---- tela de login ------------------------------------------------------
  function login(e){
    const c = cores(e);
    const tela = el("div", "pv-tela pv-login");
    tela.style.setProperty("--pv-acento", c.destaque);
    const fundo = el("div", "pv-login-fundo" + (e.login_desfoque !== "nao" ? " desfocado" : "")
                     + (e.modo === "claro" ? " claro" : ""));
    pintar(fundo, fundoDoLogin(e));
    const topo = el("div", "pv-login-topo", `${RELOGIO.curto}  ⏻`);
    const meio = el("div", "pv-login-meio");
    meio.appendChild(el("div", "pv-foto"));
    if (e.login_usuarios === "lista") meio.appendChild(el("div", "pv-nome", "seu usuário ▾"));
    else meio.appendChild(el("div", "pv-campo", "Nome"));
    meio.appendChild(el("div", "pv-campo", "Senha"));
    const bts = el("div", "pv-login-bts");
    const entrar = el("span", "pv-bt-entrar", "Entrar");
    entrar.style.color = textoSobre(c.destaque);
    bts.append(el("span", "pv-bt-vidro", "Cancelar"), entrar);
    meio.appendChild(bts);
    tela.append(fundo, topo, meio);
    if (e.login === "nao") tela.appendChild(el("div", "pv-desligada", "Tela de login do sistema (sem a da paleta)"));
    return tela;
  }

  // ---- montagem -----------------------------------------------------------
  function desenhar(e){
    const caixa = document.querySelector("#previas");
    if (!caixa) return;
    caixa.textContent = "";
    caixa.hidden = false;
    const c1 = el("div", "cartao pv-cartao");
    c1.append(el("h2", "", "Área de trabalho"), desktop(e),
              el("div", "pv-pe", "Muda na hora a cada opção; o desenho é aproximado."));
    const c2 = el("div", "cartao pv-cartao");
    c2.append(el("h2", "", "Tela de login e de bloqueio"), login(e),
              el("div", "pv-pe", "A de verdade aparece no próximo reinício; a de bloqueio muda na hora."));
    caixa.append(c1, c2);
  }

  // o fundo do login vira galeria: o papel da paleta, a imagem da pessoa e o
  // botao de escolher outra
  function galeria(o, e, escolher){
    if (o.chave !== "login_fundo") return null;
    const g = el("div", "pv-galeria");
    o.valores.forEach(v => {
      const b = el("button", "pv-mini");
      b.type = "button";
      b.setAttribute("aria-pressed", String(e[o.chave] === v));
      const img = el("span", "pv-mini-img");
      pintar(img, v === "propria"
        ? {url: `/api/login-propria.jpg?v=${versaoPropria}`, texto: "nenhuma ainda"}
        : fundoDoPapel(e));
      const nome = (o.nomes || {})[v] || v;
      b.append(img, el("span", "pv-mini-nome", nome));
      b.title = nome;
      b.addEventListener("click", () => escolher(v));
      g.appendChild(b);
    });

    const caixa = el("div", "pv-galeria-caixa");
    const acoes = el("div", "pv-escolher");
    const entrada = el("input");
    entrada.type = "file";
    entrada.accept = "image/jpeg,image/png,image/webp";
    entrada.hidden = true;
    const botao = el("button", "bt sec", "Escolher imagem…");
    botao.type = "button";
    const aviso = el("span", "pv-aviso", "JPEG, PNG ou WebP; vai para o fundo do login");
    botao.addEventListener("click", () => entrada.click());
    entrada.addEventListener("change", async () => {
      const arquivo = entrada.files && entrada.files[0];
      entrada.value = "";
      if (!arquivo) return;
      botao.disabled = true;
      aviso.classList.remove("erro");
      aviso.textContent = "Preparando a imagem…";
      try {
        const imagem = await reduzir(arquivo);
        aviso.textContent = "Enviando…";
        const r = await fetch("/api/login-imagem", {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({imagem}),
        }).then(x => x.json());
        if (!r.ok) throw new Error(r.erro || "o painel recusou a imagem");
        versaoPropria++;
        faltam.forEach(u => { if (u.startsWith("/api/login-propria")) faltam.delete(u); });
        escolher("propria");
      } catch (erro){
        aviso.textContent = "Não deu: " + erro.message;
        aviso.classList.add("erro");
        botao.disabled = false;
      }
    });
    acoes.append(botao, aviso, entrada);
    caixa.append(g, acoes);
    return caixa;
  }

  // a foto inteira de uma camera passaria do limite do painel: sai em JPEG de
  // no maximo 2560x1600, que e mais do que a tela de login precisa
  function reduzir(arquivo){
    return new Promise((ok, falha) => {
      const url = URL.createObjectURL(arquivo);
      const img = new Image();
      img.onload = () => {
        const escala = Math.min(1, 2560 / img.naturalWidth, 1600 / img.naturalHeight);
        const c = document.createElement("canvas");
        c.width = Math.round(img.naturalWidth * escala);
        c.height = Math.round(img.naturalHeight * escala);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        ok(c.toDataURL("image/jpeg", 0.9).split(",")[1]);
      };
      img.onerror = () => { URL.revokeObjectURL(url); falha(new Error("o navegador não abriu essa imagem")); };
      img.src = url;
    });
  }

  return {desenhar, galeria};
})();
