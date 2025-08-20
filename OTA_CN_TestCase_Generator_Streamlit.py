
import io, re, random
import pandas as pd
import streamlit as st

st.set_page_config(page_title="走查记录用例生成器（中文）", layout="wide")
st.title("🧪 走查记录用例生成器（中文）")
st.caption("按【模板 × 槽位 × 噪声/口语/方言 × 上下文】生成中文 Query，直接对齐你们的走查记录表头。")

def list_slot(df, name):
    if df.empty: return []
    return df[df["slot"]==name]["value"].astype(str).tolist()

def replace_slots(tpl, pools):
    import re, random
    def repl(m):
        key = m.group(1)
        vals = pools.get(key, [])
        return random.choice(vals) if vals else "{" + key + "}"
    return re.sub(r"\{([a-zA-Z0-9_]+)\}", repl, str(tpl))

def build_noise_funcs(slots_df, typos_df):
    import random
    prefix = list_slot(slots_df, "prefix") or ["那个啥","拜托啦","麻烦你"]
    suffix = list_slot(slots_df, "suffix") or ["谢谢","辛苦","多谢"]
    particle = list_slot(slots_df, "particle") or ["呗","啦","嘛"]
    dialect = list_slot(slots_df, "dialect") or ["搞快点","安逸","嚟首歌"]

    def w_typo(s: str) -> str:
        if typos_df is None or typos_df.empty: return s
        s2 = s
        for _, r in typos_df.sample(frac=1.0).iterrows():
            fr, to = str(r.get("from","")), str(r.get("to",""))
            if fr and fr in s2:
                s2 = s2.replace(fr, to, 1); break
        return s2

    def w_noise(s: str) -> str:
        t = s
        if random.random()<0.6: t = random.choice(prefix) + "…" + t
        if random.random()<0.6: t = t + random.choice(particle)
        if random.random()<0.4: t = t + "，" + random.choice(suffix)
        return t

    def w_dialect(s: str) -> str:
        if random.random()<0.5:
            return s + "，" + random.choice(dialect)
        return s

    def w_long(s: str) -> str:
        filler = "我在路上有点堵心情也一般，不过还想听点放松的，"
        return filler + s + "，如果不行也没关系你看着办吧"
    return w_typo, w_noise, w_dialect, w_long

def to_excel_bytes(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()

with st.sidebar:
    st.header("⚙️ 生成配置")
    seed = st.number_input("随机种子", value=42, min_value=0, step=1)
    per_template_samples = st.number_input("每个模板采样数", value=300, min_value=0, step=50)
    max_cases_per_intent = st.number_input("每个意图最大条数", value=4000, min_value=100, step=100)
    max_total_cases = st.number_input("全局最大条数", value=20000, min_value=1000, step=1000)
    augment_base = st.checkbox("对基础短句也加口语/错写/冗余", value=True)
    st.markdown("---")
    st.subheader("📤 上传库存 Excel（可选）")
    st.caption("需要包含 sheets：intents / templates / slots / noise_typo / contexts")
    inv = st.file_uploader("上传 .xlsx", type=["xlsx"])

import random
random.seed(42)

def default_inventory():
    intents = pd.DataFrame([
        {"intent_id":"播放_音乐","action":"播放媒体","base_phrases":"播放音乐;放一首歌;来点音乐","synonyms":"来首嗨歌;放个粤语歌听听"},
        {"intent_id":"导航_POI","action":"导航","base_phrases":"带我去{poi}，在{city}","synonyms":"去{city}的{poi}"},
        {"intent_id":"车控_空调_设定温度","action":"车控","base_phrases":"把温度设到{temp}度","synonyms":"空调调到{temp}°"},
        {"intent_id":"不支持","action":"不支持","base_phrases":"帮我点个外卖","synonyms":"买杯奶茶"},
        {"intent_id":"拒答","action":"安全拦截","base_phrases":"涉黄内容","synonyms":"辱骂语"},
    ])
    templates = pd.DataFrame([
        {"intent_id":"播放_音乐","template":"放一首{artist}的歌","test_type":"基础","note":"艺人名"},
        {"intent_id":"播放_音乐","template":"来点{genre}风格的音乐","test_type":"模糊/噪声","note":"曲风"},
        {"intent_id":"导航_POI","template":"带我去{poi}，在{city}","test_type":"基础","note":""},
        {"intent_id":"车控_空调_设定温度","template":"空调调到{temp}°","test_type":"基础","note":""},
    ])
    slots = pd.DataFrame([
        {"slot":"artist","value":"周杰伦"},{"slot":"artist","value":"林俊杰"},{"slot":"artist","value":"王菲"},
        {"slot":"genre","value":"民谣"},{"slot":"genre","value":"R&B"},{"slot":"genre","value":"摇滚"},
        {"slot":"poi","value":"医院"},{"slot":"poi","value":"加油站"},{"slot":"poi","value":"停车场"},
        {"slot":"city","value":"上海"},{"slot":"city","value":"北京"},{"slot":"city","value":"广州"},
        {"slot":"temp","value":"18"},{"slot":"temp","value":"22"},{"slot":"temp","value":"26"},
        {"slot":"prefix","value":"那个啥"},{"slot":"prefix","value":"拜托啦"},{"slot":"prefix","value":"麻烦你"},
        {"slot":"suffix","value":"谢谢"},{"slot":"suffix","value":"辛苦"},{"slot":"suffix","value":"多谢"},
        {"slot":"particle","value":"呗"},{"slot":"particle","value":"啦"},{"slot":"particle","value":"嘛"},
        {"slot":"dialect","value":"搞快点"},{"slot":"dialect","value":"安逸"},{"slot":"dialect","value":"嚟首歌"},
    ])
    noise_typo = pd.DataFrame([
        {"from":"音乐","to":"音樂"},{"from":"音乐","to":"音玥"},{"from":"播放","to":"播方"},
    ])
    contexts = pd.DataFrame([
        {"group_id":"G_多轮_换歌","step":1,"query":"放{artist}的歌","expected_intent":"播放_音乐","note":""},
        {"group_id":"G_多轮_换歌","step":2,"query":"换成{artist}的","expected_intent":"播放_音乐","note":"上下文延续"},
    ])
    return intents, templates, slots, noise_typo, contexts

if inv:
    xls = pd.ExcelFile(inv)
    def read_sheet(name): return pd.read_excel(xls, name) if name in xls.sheet_names else pd.DataFrame()
    intents_df   = read_sheet("intents")
    templates_df = read_sheet("templates")
    slots_df     = read_sheet("slots")
    noise_df     = read_sheet("noise_typo")
    contexts_df  = read_sheet("contexts")
    if any(df.empty for df in [intents_df, templates_df]):
        st.warning("intents/templates 不能为空，已回退到默认示例。")
        intents_df, templates_df, slots_df, noise_df, contexts_df = default_inventory()
else:
    intents_df, templates_df, slots_df, noise_df, contexts_df = default_inventory()

st.markdown("### 📚 意图（intents）")
st.dataframe(intents_df, use_container_width=True, height=220)
st.markdown("### 🧩 模板（templates）")
st.dataframe(templates_df, use_container_width=True, height=220)
st.markdown("### 🧰 槽位（slots）")
st.dataframe(slots_df, use_container_width=True, height=220)

with st.expander("🪛 错写/扰动（noise_typo）", expanded=False):
    st.dataframe(noise_df, use_container_width=True)
with st.expander("🗣️ 上下文（contexts）", expanded=False):
    st.dataframe(contexts_df, use_container_width=True)

st.markdown("---")
if st.button("▶️ 一键生成中文用例"):
    pools = {s: slots_df[slots_df["slot"]==s]["value"].astype(str).tolist() for s in slots_df["slot"].unique()}
    w_typo, w_noise, w_dialect, w_long = build_noise_funcs(slots_df, noise_df)

    rows = []
    def push(q, intent, action, ttype, diff=1, group="", ctx="", note=""):
        rows.append({
            "Query文本": q, "预期意图": intent, "预期动作": action or "",
            "测试类型": ttype, "难度等级": diff, "分组": group, "上下文": ctx, "备注": note
        })

    # 基础与同义
    for _, r in intents_df.iterrows():
        intent = str(r.get("intent_id","")).strip()
        if not intent: continue
        action = str(r.get("action","")).strip()
        base = [x for x in re.split(r"[;；]", str(r.get("base_phrases",""))) if x.strip()]
        syns = [x for x in re.split(r"[;；]", str(r.get("synonyms",""))) if x.strip()]
        gb, gs = f"G_{intent}_B", f"G_{intent}_S"
        for q in base[:5]:
            q2 = replace_slots(q, pools)
            push(q2, intent, action, "基础", 1, gb)
            push(w_typo(q2), intent, action, "模糊/噪声", 2, f"G_{intent}_N", "", "错写/繁简")
            push(w_noise(q2), intent, action, "模糊/噪声", 2, f"G_{intent}_N", "", "噪声冗余")
            push(w_dialect(q2), intent, action, "模糊/噪声", 2, f"G_{intent}_N", "", "方言口语")
        for q in syns[:5]:
            q2 = replace_slots(q, pools)
            push(q2, intent, action, "基础", 2, gs, "", "同义替换")

    # 模板采样（海量）
    per_tpl = 300
    max_intent = 4000
    max_total  = 20000
    tpl_grouped = templates_df.groupby("intent_id")
    count_per_intent = {}

    for intent, grp in tpl_grouped:
        action = intents_df.loc[intents_df["intent_id"]==intent, "action"]
        action = action.iloc[0] if len(action)>0 else ""
        group_t = f"G_{intent}_TPL"
        tpls = grp[["template","test_type","note"]].values.tolist()
        samples = 0
        while count_per_intent.get(intent,0) < max_intent and samples < per_tpl*max(1,len(tpls)):
            tpl, ttype, note = random.choice(tpls)
            q = replace_slots(tpl, pools)
            push(q, intent, action, ttype or "基础", 1 if (ttype or "")=="基础" else 2, group_t, "", note or "")
            count_per_intent[intent] = count_per_intent.get(intent,0)+1
            samples += 1
            if len(rows) >= max_total: break
        if len(rows) >= max_total: break

    # 上下文/多轮
    for gid, grp in contexts_df.groupby("group_id"):
        prev = ""
        grp = grp.sort_values("step") if "step" in grp.columns else grp
        for _, r in grp.iterrows():
            q = replace_slots(r.get("query",""), pools)
            intent = str(r.get("expected_intent","")).strip()
            push(q, intent, "", "上下文", 2, str(gid), prev, str(r.get("note","")))
            prev = f"上一句：{q}"

    df = pd.DataFrame(rows).drop_duplicates(subset=["Query文本","预期意图","测试类型","上下文"]).reset_index(drop=True)
    st.success(f"已生成 {len(df)} 条中文用例")
    st.dataframe(df.head(50), use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    xlsx = to_excel_bytes(df)
    st.download_button("⬇️ 下载 CSV（UTF-8）", data=csv, file_name="test_cases_cn.csv", mime="text/csv")
    st.download_button("⬇️ 下载 Excel（xlsx）", data=xlsx, file_name="test_cases_cn.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
