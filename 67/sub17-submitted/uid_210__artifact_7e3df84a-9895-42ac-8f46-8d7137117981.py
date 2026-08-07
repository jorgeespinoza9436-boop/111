"""Q5 — RetainLattice: dual-path research with origin-locked seal.

HardnessSwitcher routes easy asks to LightCorridor and hard asks to
HeavyCorridor. HeavyCorridor pins premises via retain_evidence, reads pages
with page_grep/page_read, builds an evidence tableau, and seals under a
nominee lattice that gap-fills unresolved constraints before commit.

Named origins (Wikipedia, Worldometer, The Numbers, …) are parsed from the
ask, injected into the orbit seed, and recovered with a site-biased hunt if
still unmet before the forced seal — so aggregators cannot replace the
pinned source.
"""

from __future__ import annotations 
import asyncio 
from harnyx_miner_sdk .api import LlmThinkingConfig ,llm_chat 
from harnyx_miner_sdk .decorators import entrypoint 
from harnyx_miner_sdk .query import Query ,Response 

class HeavyCorridor :

    def _compile (self ):
        import asyncio 
        import json 
        import re 
        from time import monotonic 
        from harnyx_miner_sdk .api import fetch_page ,llm_chat ,search_web ,tooling_info 
        from harnyx_miner_sdk .decorators import entrypoint 
        from harnyx_miner_sdk .query import CitationRef ,CitationSlice ,Query ,Response 
        VERSION_P ='q5-r1-sliceproof-20260805-sliceproof-doctrine'
        LLM_TRACK_A ='chutes'
        LLM_TRACK_B ='ai_gateway'
        ORBIT_MODEL_A ='zai-org/GLM-5-TEE'
        ORBIT_MODEL_B ='zai/glm-5.2-fast'
        INSPECT_MODEL ='Qwen/Qwen3.6-27B-TEE'
        OUTLINE2_MODEL ='Qwen/Qwen3.6-27B-TEE'
        FALLBACK2_MODEL ='deepseek-ai/DeepSeek-V3.2-TEE'
        SCOUT_PROVIDER ='parallel'
        WALL_RATION_S =266.0 
        DOSSIER_LIMIT2_S =50.0 
        TICK_LIMIT2_S =75.0 
        INSPECT_LIMIT2_S =28.0 
        SCOUT_LIMIT2_S =18.0 
        PULL_LIMIT2_S =16.0 
        FINALE_AT_S =90.0 
        LOWER_REMAINDER_S =8.0 
        UPPER_TICKS =15 
        INSPECT_SURPLUS_TICKS =2 
        VERDICT_REWORK_TICKS =2 
        RECOVER_LIMIT2_S =55.0 
        INSPECT_REWORK_UPPER_S =70.0 
        INSPECT_LOWER_SLACK_S =130.0 
        BREVIARY_REMAINDER_S =14.0 
        SCOUT_PASSAGE_GLYPHS =550 
        _VAULT_TEXT_LID =400000 
        FOLIO2_LOCATE_PANE =700 
        FOLIO2_LOCATE_UPPER_HITS =6 
        FOLIO2_SCAN_UPPER_GLYPHS =12000 
        PIN_PAD_GLYPHS =260 
        PIN_UPPER_PER_SLOT =6 
        PIN_LOWER_CITATION2 =12 
        PULL_HEAD_GLYPHS =3000 
        PULL_PANE_GLYPHS =3600 
        FOOTNOTE_LOWER_REACH_GLYPHS =6000 
        FOOTNOTE_UPPER_REF_GLYPHS =14000 
        PULL_PANES_PER_FOLIO2 =3 
        PULL_STARK_GLYPHS =6500 
        VERDICT_GLYPH_LID =60000 
        FOOTNOTE_LID =24 
        SPECIMEN_GLYPH_RATION =105000 
        DOSSIER_LOWER_USD =0.03 
        INSPECT_LOWER_USD =0.05 
        FINALE_LOWER_USD =0.02 
        _BURN ={'left':None }

        def _burn_annotation (bundle )->None :
            ration =getattr (bundle ,'budget',None )
            remain =getattr (ration ,'session_remaining_budget_usd',None )
            if isinstance (remain ,(int ,float )):
                _BURN ['left']=float (remain )

        def _burn_remain ()->float :
            remain =_BURN ['left']
            if isinstance (remain ,(int ,float )):
                return float (remain )
            return 1.0 
        ORBIT_IMPLEMENTS =[{'type':'function','function':{'name':'web_search','description':'Web search. Returns numbered results, each with title, url and excerpt.','parameters':{'type':'object','properties':{'query':{'type':'string','description':'the search query'}},'required':['query']}}},{'type':'function','function':{'name':'sec_filing','description':"Resolve a company's SEC filing to its primary document URL on sec.gov (exact form + year, from EDGAR's own index). Use for questions about a specific filing (10-K, 10-Q, 8-K, DEF 14A…), then read_page the returned URL with a focus hint for the Item/section.",'parameters':{'type':'object','properties':{'company':{'type':'string','description':"company name or ticker, e.g. 'Apple' or 'AAPL'"},'form':{'type':'string','description':"filing form, e.g. '10-K', '10-Q', '8-K', 'DEF 14A'"},'year':{'type':'string','description':"optional report (fiscal) year, e.g. '2019' (omit for latest)"}},'required':['company','form']}}},{'type':'function','function':{'name':'read_page','description':'Fetch a URL and return its main text. Large pages show the head plus the few regions most relevant to the question; pass a focus hint to steer which regions.','parameters':{'type':'object','properties':{'url':{'type':'string','description':'URL to fetch'},'focus':{'type':'string','description':'optional phrase to locate inside the page (section name, table label, entity)'}},'required':['url']}}},{'type':'function','function':{'name':'page_grep','description':'Search INSIDE a page you already fetched, by regex or literal text, and get every match with its surrounding context and character offset. Use this when read_page showed you the head of a long page but the value you need is deeper in it -- do not re-fetch, grep it.','parameters':{'type':'object','properties':{'url':{'type':'string','description':'URL of a page already fetched this run'},'pattern':{'type':'string','description':'regex or literal string to find, e.g. a city name, a year, a column label'}},'required':['url','pattern']}}},{'type':'function','function':{'name':'page_read','description':'Read an arbitrary character range of a page you already fetched. Use the offsets page_grep reports to read the full table or section around a match.','parameters':{'type':'object','properties':{'url':{'type':'string','description':'URL already fetched'},'offset':{'type':'integer','description':'start character offset'},'length':{'type':'integer','description':'how many characters to read (max 12000)'}},'required':['url','offset']}}},{'type':'function','function':{'name':'retain_evidence','description':"Keep the exact source text that proves a claim you are about to make. Pass the result number and the verbatim quote from that result so the citation slice contains the proving words.",'parameters':{'type':'object','properties':{'source':{'type':'string','description':'result number to quote from, e.g. 3'},'quote':{'type':'string','description':'verbatim text copied from that result that states the fact'}},'required':['source','quote']}}}]

        _NAMED_ORIGIN_RE_H = re.compile(
            r"\b(?:according to|per|from|listed (?:in|on)|in the)\s+"
            r"((?:the\s+)?[A-Z][\w.'&-]*(?:\s+[A-Z][\w.'&-]*){0,4})",
            re.S,
        )
        _ORIGIN_WORD_RE_H = re.compile(
            r"\b(wikipedia|wikidata|imdb|britannica|usgs|nasa|noaa|"
            r"baseball-reference|basketball-reference|box office mojo|boxofficemojo|"
            r"rotten tomatoes|metacritic|billboard|sec|edgar|eurostat|world bank|imf|"
            r"census|worldometer|worldometers|the numbers|thenumbers|citypopulation|"
            r"macrotrends|statista|our world in data)\b",
            re.I,
        )
        _ORIGIN_NOUN_RE_H = re.compile(
            r"\b(?:wiki\w*|article|page|site|database|dataset|data|table|list|index|"
            r"factsheet|report|filing|registry|catalog(?:ue)?|encyclopedia|archive|"
            r"records?|statistics|census|survey|bulletin|\.(?:com|org|net|gov|edu))\b",
            re.I,
        )
        _ORIGIN_SITE_MAP_H = {
            "wikipedia": "wikipedia.org", "worldometer": "worldometers.info",
            "worldometers": "worldometers.info", "the numbers": "the-numbers.com",
            "thenumbers": "the-numbers.com", "box office mojo": "boxofficemojo.com",
            "boxofficemojo": "boxofficemojo.com", "imdb": "imdb.com",
            "sec": "sec.gov", "edgar": "sec.gov", "world bank": "worldbank.org",
            "imf": "imf.org", "census": "census.gov",
        }

        def _named_origins_h(query2: str) -> list[str]:
            found: list[str] = []
            for m in _ORIGIN_WORD_RE_H.finditer(query2 or ""):
                name = m.group(1).strip()
                if name.lower() not in {f.lower() for f in found}:
                    found.append(name)
            for m in _NAMED_ORIGIN_RE_H.finditer(query2 or ""):
                name = re.sub(r"^the\s+", "", m.group(1).strip(), flags=re.I).strip(" .,'")
                if not _ORIGIN_NOUN_RE_H.search(name):
                    continue
                if 2 < len(name) < 60 and name.lower() not in {f.lower() for f in found}:
                    found.append(name)
            return found[:4]

        def _origin_site_h(name: str) -> str:
            key = (name or "").strip().lower()
            return _ORIGIN_SITE_MAP_H.get(key, key.replace(" ", ""))

        def _origin_edict_h(names: list[str]) -> str:
            listed = ", ".join(names)
            return (
                f"NAMED ORIGIN LOCK — this ask pins the answer to: {listed}. "
                f"You MUST hunt and read_page THAT origin (try site: filters). "
                f"Aggregators with matching figures score 0.0 if the named origin "
                f"was not cited. Prefer the named origin's exact figures when they "
                f"conflict. Re-fetch with a focus so the cited excerpt itself shows "
                f"those figures (slice must LITERALLY contain the digits/names)."
            )

        def _vault_covers_origin(vault, names: list[str]) -> bool:
            if not names or not getattr(vault, "rows", None):
                return not names
            blob = " ".join(
                ((r.get("url") or "") + " " + (r.get("title") or "") + " " + (r.get("preview") or "")).lower()
                for r in vault.rows
            )
            for name in names:
                site = _origin_site_h(name).lower()
                token = name.lower()
                if site and site in blob:
                    return True
                if token and token.replace(" ", "") in blob.replace(" ", ""):
                    return True
            return False

        async def _origin_recovery_h(query2: str, vault, cutoff: float) -> int:
            """Fetch unmet named origins before forced seal."""
            names = _named_origins_h(query2)
            if not names or _vault_covers_origin(vault, names):
                return 0
            if cutoff - monotonic() < 45.0:
                return 0
            filled = 0
            for name in names[:2]:
                site = _origin_site_h(name)
                q = f"site:{site} {query2[:160]}" if site and "." in site else f"{name} {query2[:160]}"
                try:
                    out = await asyncio.wait_for(_do_scout(q, vault), timeout=min(22.0, cutoff - monotonic() - 8.0))
                    _seal_implement_emission(out, vault)
                    filled += 1
                except Exception:
                    continue
                # also try a plain name hunt
                try:
                    out2 = await asyncio.wait_for(
                        _do_scout(f"{name} {query2[:120]}", vault),
                        timeout=min(18.0, cutoff - monotonic() - 8.0),
                    )
                    _seal_implement_emission(out2, vault)
                    filled += 1
                except Exception:
                    pass
            return filled


        ORBIT_STATUTE ='You are solving a dense, multi-clause factual brief. Scoring is head-to-head against a strong reference; only claims whose citation CONTAINS the proving source text earn credit.\n\nPIN THE PROOF: the moment a decisive value appears, call retain_evidence(source, quote) with the exact wording from that result. Do this for every condition you test and every figure you report. An answer whose citations lack its numbers loses to an otherwise identical answer that pinned them.\nPIN THE PREMISES TOO: every entity, work, date or figure the question itself NAMES must be traceable. Background you "already knew" still needs a retained quote once confirmed — graders ding missing premise citations even when the final entities are right.\n\nDUAL RANKINGS: top-N on two metrics means the INTERSECTION of both lists. TABLE NAMES: copy exactly as printed (e.g. DR Congo). EMPTY STRUCTURED OUTPUTS SCORE ZERO — never return [] when evidence exists. SET COMPLETENESS: enumerate the full class, then apply every filter.\n\nGO DEEPER ON THE SAME PAGE: read_page shows the head plus a few dense regions. If the needed value is missing, call page_grep(url, pattern) to locate it anywhere on that page, then page_read around the reported offset. Re-searching a page you already hold is wasteful.\n\nWORKFLOW: reason in constraints and nominees. Sketch the nominee basin from prior knowledge, then verify every load-bearing fact (names, figures, dates, rankings) with web_search/read_page. Push every nominee through every stated constraint; one lookup per fact beats one vague sweep. SPLIT ASKS: when the brief has two distinct sub-asks, answer BOTH substantively — half-coverage of both sides beats full coverage of one. PARALLEL LOOKUPS: independent facts belong in SEVERAL tool calls in ONE tick so they run together. TABLES: honour qualifier columns (Owned vs Leased, year, segment); only count rows matching every qualifier, and quote the cells you used. Named origins (Worldometer, The Numbers, Wikipedia, Box Office Mojo, a 10-K, Nielsen) must be opened at THAT page — for SEC filings, use sec_filing to resolve the primary EDGAR document, then read_page with an Item/section focus.\n\nFOOTNOTE EVERYTHING: place [n] immediately after the sentence that carries the claim — including entities you exclude. Prefer the most authoritative result that states the claim (official database/filing over aggregator or blog). HARD CONSTRAINTS NEED THEIR OWN CITATIONS: proving only the nominee basin leaves the decisive filter unsupported.\n\nSOURCE LABELS: if a named source is unreachable but other authoritative evidence establishes the same facts, state those facts confidently with their [n]. Do not lead with, dwell on, or append that the named source was missing — reserve absence language for a fact that is missing everywhere.\n\nINTERNAL CONSISTENCY: the opening must name exactly the entities your cited body supports. If the body diverges, rewrite the lead — never leave a weaker fallback up top.\n\nANSWER FORM: sentence one IS the answer — the exact entities/values/list requested. Never open with \'Based on…\', \'From my research…\', or \'I can provide a partial answer\'. ANSWER THE ASKED KIND: series → series name; film → film; country → country. THE BASIN IS THE WHOLE NAMED CLASS: enumerate the broad class the question ranges over, then apply constraints one by one and show whom each eliminates. Never present only survivors as the basin. Give ONE LINE PER BASIN MEMBER — each qualifier with its cited attribute AND each reject with its cited failing constraint. Never batch rejects into one clause. If a member\'s constraint is unsettled, KEEP it among the qualifiers and cite the strongest verified fact; never annotate what you could not check. OUTPUT DIRECTIVES ARE LITERAL: decide whether a phrase shapes PRINTING or selects ENTITIES. \'list them without the word "X"\' deletes X from printed names; \'whose title does not contain "X"\' filters the basin. Sort/order/count/comma-separated instructions govern the answer line; still attach the proof below. COPY SOURCE STRINGS VERBATIM when a source is named — no parenthetical "familiar" alternatives, no anglicised transliterations. EXCEPTION: if the brief demands ONLY the answer (\'output only\', \'nothing else\', …), emit the bare answer line with no [n] on that line, then the proof section below with citations (citations are harvested from the proof). When ORDER is demanded, sort the ANSWER LINE itself and print the sort key beside each item; one out-of-sequence member fails the whole set. DERIVED VALUES: list every input with citations first, then show the arithmetic. ROUNDED FIGURE = WRONG SOURCE: trailing zeros, \'about\', chart labels — refetch the exact figure from the named measuring body; quote the rounded value only as corroboration. Once tools close, commit the best held figure without remarking on precision. EXACT REPORTING: preserve notation (58.58% ≠ 58.6%; \'p < 0.0001\' ≠ \'P < .001\'). Give ranges and point values both when they conflict. Convert units when asked. Bind claims to the exact actor/target/date-window/instrument. Never write \'(verify)\' or uncertainty markers in the final answer.\n\nAMBIGUOUS METRIC? Answer BOTH defensible readings, each labelled and cited — silent choice of one reading still scores as wrong if the grader used the other.\n\nAPPLY CONSTRAINTS LITERALLY: copy each nominee\'s exact value, then test the comparator as written (\'more than 25\' is strictly >25; inclusive endpoints for \'between\'). Convert rate conditions into concrete integer tests. EXCLUDE ONLY ON PROOF: name the failed constraint with a cited fact — never drop a nominee because it "looks weaker". If failure is uncertain, KEEP the nominee. SAY NO MORE THAN THE CITATION: do not upgrade verbs or invent adjacent counts.\n\nNEVER NARRATE THE LEDGER: ban sentences about what results do or do not contain. A substantive negative about the WORLD is fine when true. If a datum cannot be verified, commit the best-supported value and move on. Narrow exception: reasoned impossibility of a figure that truly does not exist in any published form — name the dataset and why — may appear in the first line as a world-fact.\n\nCLOSE: never mix tool calls with the final answer in one tick. When constraints are verified (or best-effort covered), write the complete cited answer.'

        def _finale_edict (seconds_remain :float )->str :
            return f"TIME IS UP (~{int(seconds_remain)}s left). No more tool calls. Write the complete final answer NOW from the numbered results above plus your knowledge: the FIRST words are the answer entities (no 'Based on…' preamble, no 'partial answer' framing, no '(verify)' markers), cite [n] on every claim, keep the required format. A cited partial answer scores; a refusal or a remark about insufficient evidence scores zero."+(''if seconds_remain >=60 else ' BREVITY OVERRIDE: too little time remains for a line per pool member. Lead with the answer entities, then give the qualifiers one cited line each and compress the rejects into a single cited line. A complete short answer beats a long one that never finishes.')
        _ENSEMBLE_HINT_RE =re .compile ('\\b(?:list|name|identify|enumerate)\\b[^?]{0,40}\\b(?:all|every|each|the)\\b|\\bhow many\\b|\\bwhich (?:movies|films|series|countries|companies|states|cities|books|albums|artists|players|teams|species|languages|banks|universities|agencies|models|products)\\b',re .IGNORECASE )
        _ENSEMBLE_CONNECTIVE_RE =re .compile ('\\b(?:both|also|and (?:also|had|has|was|were)|as well as)\\b',re .IGNORECASE )
        _PLURAL2_HEAD_RE =re .compile ('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b',re .IGNORECASE )
        _PLURAL2_FALSE =frozenset ('was is has does its this thus across process business series species news status analysis basis less unless always perhaps'.split ())
        _ONE_VICTOR_RE =re .compile ('\\b(?:highest|lowest|largest|smallest|most|least|greatest|fewest|longest|shortest|first|last|best|worst|only|oldest|youngest|newest|biggest)\\b',re .IGNORECASE )
        _EST_STOP_P =frozenset ('interest honest modest protest request suggest forest harvest invest manifest contest arrest digest earnest conquest tempest midwest northwest southwest unrest bequest behest attest molest ingest infest detest incest armrest backrest pretest headrest footrest'.split ())
        _EST_RE_P =re .compile ('\\b([a-z]{3,})est\\b')

        def _has_apex (text :str )->bool :
            if _ONE_VICTOR_RE .search (text or ''):
                return True 
            for m_p in _EST_RE_P .finditer (text or ''):
                if m_p .group (0 ).lower ()not in _EST_STOP_P :
                    return True 
            return False 

        def _needs_apex_proof (query2 :str )->bool :
            q_p =' '.join ((query2 or '').split ())
            if not q_p :
                return False 
            return _has_apex (q_p )or bool (re .search ('\\b(?:most|least) (?:common|frequent|number|amount)\\b|\\bhow many\\b',q_p ,re .I ))
        APEX_STATUTE2 ="SUPERLATIVE / TALLY — SHOW THE TABLE. The answer is one item, but you cannot know it without the whole basin. Before naming a winner, list every member with its deciding metric and [n], then compare. Sentence one names the winner; the proof keeps the full comparison. Skipping the table under-supports a correct pick."

        def _needs_ensemble_fullness (query2 :str )->bool :
            q_p =' '.join ((query2 or '').split ())
            if _ENSEMBLE_HINT_RE .search (q_p ):
                return True 
            m_p =_PLURAL2_HEAD_RE .search (q_p )
            if m_p and m_p .group (1 ).lower ()not in _PLURAL2_FALSE :
                if not _has_apex (q_p )or re .search ('\\b(?:all|every|each)\\b',q_p ,re .IGNORECASE ):
                    return True 
            return bool (re .search ('\\bwhich\\b',q_p ,re .IGNORECASE ))and bool (_ENSEMBLE_CONNECTIVE_RE .search (q_p ))
        ENSEMBLE_STATUTE2 ="SET ANSWER: this question asks for a set. Missing a qualifying member scores the same as wrong — enumerate the basin, test every constraint, list survivors and rejects with citations.\n1. Build the basin from the broad named class.\n2. For each constraint, show who fails it with [n].\n3. Sentence one = the full surviving set in the requested shape.\n4. Proof: one line per survivor (qualifying attribute + [n]) and one line per reject (failed constraint + [n]).\n5. If a constraint is unsettled, retain the member among survivors and cite what you did verify — never silently drop.\n6. Obey print directives (order, separators, deletions) on the answer line; proof still follows."

        class SpecimenVault :

            def __init__ (self )->None :
                self .rows :list [dict ]=[]

            def add (self ,receipt_id :str ,result_id :str ,note_len :int ,kind :str ,spans :list [tuple [int ,int ]]|None ,title :str ='',url :str ='',preview :str ='',text :str ='')->int :
                self .rows .append ({'receipt_id':receipt_id ,'result_id':result_id ,'note_len':note_len ,'kind':kind ,'title':(title or '')[:160 ],'url':(url or '')[:300 ],'preview':(preview or '')[:1200 ],'spans':spans ,'text':(text or '')[:_VAULT_TEXT_LID ],'retained':[]})
                return len (self .rows )

            def ref_for (self ,index2 :int )->CitationRef |None :
                if not 1 <=index2 <=len (self .rows ):
                    return None 
                slot =self .rows [index2 -1 ]
                if slot .get ('kind')=='reserved':
                    return None 
                if not slot ['receipt_id']or not slot ['result_id']:
                    return None 
                spans =slot ['spans']
                if spans :
                    note_len =int (slot ['note_len']or 0 )
                    shown_p :list [list [int ]]=[]
                    for reach in spans [:4 ]:
                        start =max (0 ,min (int (reach [0 ]),note_len ))
                        end =max (start +1 ,min (int (reach [1 ]),note_len ))
                        shown_p .append ([start ,end ])
                    pinned =[]
                    for a_p ,b_p in slot .get ('retained')or []:
                        a_p =max (0 ,min (int (a_p ),note_len ))
                        b_p =max (a_p +1 ,min (int (b_p ),note_len ))
                        pinned .append ([a_p ,b_p ])
                    if pinned :
                        shown_p =pinned 
                    shown_p .sort ()
                    merged_p :list [list [int ]]=[]
                    for s_p ,e_p in shown_p :
                        if merged_p and s_p <=merged_p [-1 ][1 ]:
                            merged_p [-1 ][1 ]=max (merged_p [-1 ][1 ],e_p )
                        else :
                            merged_p .append ([s_p ,e_p ])
                    base_p =sum ((e_p -s_p for s_p ,e_p in merged_p ))
                    room_p =max (0 ,FOOTNOTE_UPPER_REF_GLYPHS -base_p )
                    if merged_p and note_len and room_p :
                        surplus =room_p //len (merged_p )
                        for w_p in merged_p :
                            pad_p =min (surplus ,max (0 ,FOOTNOTE_LOWER_REACH_GLYPHS -(w_p [1 ]-w_p [0 ])))
                            if pad_p :
                                remain =min (pad_p //2 ,w_p [0 ])
                                w_p [0 ]-=remain 
                                rest_p =pad_p -remain 
                                right_p =min (rest_p ,note_len -w_p [1 ])
                                w_p [1 ]+=right_p 
                                w_p [0 ]=max (0 ,w_p [0 ]-(rest_p -right_p ))
                        merged_p .sort ()
                        grown_p :list [list [int ]]=[]
                        for s_p ,e_p in merged_p :
                            if grown_p and s_p <=grown_p [-1 ][1 ]:
                                grown_p [-1 ][1 ]=max (grown_p [-1 ][1 ],e_p )
                            else :
                                grown_p .append ([s_p ,e_p ])
                        merged_p =grown_p 
                    slices =[CitationSlice (start =s_p ,end =e_p )for s_p ,e_p in merged_p if e_p >s_p ]
                    if not slices :
                        return None 
                    return CitationRef (receipt_id =slot ['receipt_id'],result_id =slot ['result_id'],slices =slices )
                return None 
        _WORD_RE_P =re .compile ("[a-z0-9][a-z0-9'.\\-]{2,}")
        _STOP_P =frozenset ('the and for with from that this have has was were are is been its their which what when where who how many much according also into over under between during against about after before while other more most than'.split ())

        def _keystone_lexemes (text :str )->set [str ]:
            return {w_p for w_p in _WORD_RE_P .findall ((text or '').casefold ())if w_p not in _STOP_P }
        _VALUE_CUE_RE_P =re .compile ('\\d{1,4}\\s*[-–—]\\s*\\d{1,4}|\\d[\\d,]*(?:\\.\\d+)?\\s*%?')
        _CUE_LOWER_LEN =3 
        _THIN_CUE_RE =re .compile ('^\\d{1,4}$')

        def _value_cues_p (*texts_p :str )->set [str ]:
            cues :set [str ]=set ()
            for text in texts_p :
                for crude in _VALUE_CUE_RE_P .findall (text or ''):
                    token_p =crude .replace (' ','').replace ('—','-').replace ('–','-')
                    token_p =token_p .rstrip ('.,').casefold ()
                    if len (token_p )<_CUE_LOWER_LEN or _THIN_CUE_RE .match (token_p ):
                        continue 
                    cues .add (token_p )
                    if token_p .endswith ('%'):
                        bare_p =token_p [:-1 ]
                        if len (bare_p )>=_CUE_LOWER_LEN and (not _THIN_CUE_RE .match (bare_p )):
                            cues .add (bare_p )
            return cues 

        def _prime_panes (annotation :str ,lexemes :set [str ],width_p :int ,k :int =1 ,cues :set [str ]|None =None )->list [tuple [int ,int ]]:
            n_p =len (annotation )
            if n_p <=width_p :
                return [(0 ,n_p )]
            step_p =max (600 ,width_p //3 )
            low_p =annotation .lower ().replace ('–','-').replace ('—','-')
            scored_p :list [tuple [int ,int ,int ]]=[]
            pos_p =0 
            cue_ensemble =cues or frozenset ()
            while pos_p <n_p :
                seg_p =low_p [pos_p :pos_p +width_p ]
                hits_p =sum ((1 for t_p in lexemes if t_p in seg_p ))
                cue_hits_p =sum ((1 for c_p in cue_ensemble if c_p in seg_p ))
                scored_p .append ((cue_hits_p ,hits_p ,pos_p ))
                if pos_p +width_p >=n_p :
                    break 
                pos_p +=step_p 
            scored_p .sort (key =lambda hs :(-hs [0 ],-hs [1 ],hs [2 ]))
            picked_p :list [tuple [int ,int ]]=[]
            for cue_hits_p ,hits_p ,start in scored_p :
                if len (picked_p )>=max (1 ,k ):
                    break 
                end =min (n_p ,start +width_p )
                if any ((start <pe_p and ps_p <end for ps_p ,pe_p in picked_p )):
                    continue 
                if picked_p and hits_p <=0 and (cue_hits_p <=0 ):
                    continue 
                picked_p .append ((start ,end ))
            picked_p .sort ()
            return picked_p or [(0 ,min (n_p ,width_p ))]
        _SLOT_P ='\x00{}\x00'

        class ImplementOutcome :

            def __init__ (self ,text :str ,rows :list [dict ]|None =None )->None :
                self .text =text 
                self .rows =rows or []

        def _seal_implement_emission (out_p ,vault :SpecimenVault )->str :
            if isinstance (out_p ,str ):
                return out_p 
            if not isinstance (out_p ,ImplementOutcome ):
                return f'# tool crashed: {out_p}'
            text =out_p .text 
            for i_p ,slot in enumerate (out_p .rows ):
                n_p =vault .add (slot ['receipt_id'],slot ['result_id'],slot ['note_len'],slot ['kind'],slot ['spans'],title =slot .get ('title',''),url =slot .get ('url',''),preview =slot .get ('preview',''),text =slot .get ('text',''))
                text =text .replace (_SLOT_P .format (i_p ),str (n_p ))
            return text 
        _SITE2_OP_RE =re .compile ('\\bsite:\\S+\\s*',re .I )

        def _soften_inquiry (q_p :str )->str :
            out_p =_SITE2_OP_RE .sub ('',q_p or '').replace ('"',' ')
            return ' '.join (out_p .split ())

        async def _do_scout (inquiry_text :str ,vault :SpecimenVault ):
            if not inquiry_text .strip ():
                return '# web_search: empty query'
            bundle =None 
            fired_p :set [str ]=set ()
            for attempt_p ,permit_repeat in ((inquiry_text ,False ),(inquiry_text ,True ),(_soften_inquiry (inquiry_text ),False )):
                if not attempt_p .strip ()or (attempt_p in fired_p and (not permit_repeat )):
                    continue 
                fired_p .add (attempt_p )
                try :
                    bundle =await search_web (attempt_p ,provider =SCOUT_PROVIDER ,num =8 ,timeout =SCOUT_LIMIT2_S )
                    if getattr (bundle ,'results',None ):
                        break 
                except Exception :
                    bundle =None 
            if bundle is None :
                return f'# web_search({inquiry_text!r}) failed'
            _burn_annotation (bundle )
            receipt_p =str (getattr (bundle ,'receipt_id','')or '')
            outcomes =list (getattr (bundle ,'results',None )or [])
            if not receipt_p :
                return f'# web_search({inquiry_text!r}): no citable results'
            rows :list [dict ]=[]
            lines_p =[f'# web_search({inquiry_text!r}): {len(outcomes)} results']
            for unit in outcomes :
                rid_p =getattr (unit ,'result_id',None )
                if not isinstance (rid_p ,str )or not rid_p :
                    continue 
                annotation =getattr (unit ,'note',None )or ''
                if not annotation .strip ():
                    continue 
                n_len_p =len (annotation )
                reach =[(0 ,min (max (SCOUT_PASSAGE_GLYPHS ,100 ),n_len_p ))]if n_len_p >=100 else [(0 ,n_len_p )]if n_len_p else None 
                title =(getattr (unit ,'title',None )or '').strip ()
                url =(getattr (unit ,'url',None )or '').strip ()
                rows .append ({'receipt_id':receipt_p ,'result_id':rid_p ,'note_len':n_len_p ,'kind':'search','spans':reach ,'title':title ,'url':url ,'preview':annotation [:SCOUT_PASSAGE_GLYPHS ],'text':annotation })
                lines_p .append (f'[{_SLOT_P.format(len(rows) - 1)}] {title} — {url}\n    {annotation[:SCOUT_PASSAGE_GLYPHS]}')
            return ImplementOutcome ('\n'.join (lines_p ),rows )

        async def _do_pull (url :str ,focus_p :str ,query2 :str ,vault :SpecimenVault )->str :
            if not url .strip ():
                return '# read_page: empty url'
            bundle =None 
            for _attempt_p in (0 ,1 ):
                try :
                    bundle =await fetch_page (url ,provider =SCOUT_PROVIDER ,timeout =PULL_LIMIT2_S )
                    if getattr (bundle ,'results',None ):
                        break 
                except Exception :
                    bundle =None 
            if bundle is None :
                return f'# read_page({url!r}) failed'
            _burn_annotation (bundle )
            receipt_p =str (getattr (bundle ,'receipt_id','')or '')
            outcomes =list (getattr (bundle ,'results',None )or [])
            if not outcomes or not receipt_p :
                return f'# read_page({url!r}): no content'
            unit =outcomes [0 ]
            rid_p =getattr (unit ,'result_id',None )
            annotation =getattr (unit ,'note',None )or ''
            if not isinstance (rid_p ,str )or not rid_p or (not annotation .strip ()):
                return f'# read_page({url!r}): no usable content'
            if len (annotation )<=PULL_STARK_GLYPHS :
                slot ={'receipt_id':receipt_p ,'result_id':rid_p ,'note_len':len (annotation ),'kind':'fetch','spans':[(0 ,len (annotation ))],'title':url ,'url':url ,'preview':annotation [:1200 ],'text':annotation }
                return ImplementOutcome (f'# read_page({url!r}) -> [{_SLOT_P.format(0)}] full page, {len(annotation)} chars\n{annotation}',[slot ])
            lexemes =_keystone_lexemes (query2 )|_keystone_lexemes (focus_p )
            panes =_prime_panes (annotation ,lexemes ,PULL_PANE_GLYPHS ,k =PULL_PANES_PER_FOLIO2 ,cues =_value_cues_p (query2 ,focus_p ))
            slot ={'receipt_id':receipt_p ,'result_id':rid_p ,'note_len':len (annotation ),'kind':'fetch','spans':[(0 ,PULL_HEAD_GLYPHS )]+list (panes ),'title':url ,'url':url ,'preview':annotation [panes [0 ][0 ]:panes [0 ][0 ]+1200 ],'text':annotation }
            head_p =annotation [:PULL_HEAD_GLYPHS ]
            sections_p =''.join ((f'\n--- section @{s_p} ---\n{annotation[s_p:e_p]}'for s_p ,e_p in panes ))
            return ImplementOutcome (f"# read_page({url!r}) -> [{_SLOT_P.format(0)}] {len(annotation)} chars total; head + the {len(panes)} most relevant section(s) shown ({', '.join((f'{s_p}-{e_p}' for s_p, e_p in panes))}). If the answer set may continue elsewhere in this page, call read_page again with a different focus.\n--- head ---\n{head_p}{sections_p}",[slot ])
        _EDGAR_TICKERS_HREF ='https://www.sec.gov/files/company_tickers.json'
        _EDGAR_SUBMISSIONS_HREF ='https://data.sec.gov/submissions/CIK{cik10}.json'
        _EDGAR_INSTRUMENT_HREF ='https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}'
        _EDGAR_PULL_LIMIT2_S =26.0 
        _EDGAR_LOWER_SLACK_S =40.0 
        _EDGAR_CISTERN :dict ={}
        _EDGAR_STOPWORDS =frozenset ('inc incorporated corp corporation company companies co ltd limited llc plc lp llp group holdings the'.split ())
        _EDGAR_ALNUM_RE =re .compile ('[a-z0-9]+')

        def _edgar_tokens (text :str )->list [str ]:
            return [w_p for w_p in _EDGAR_ALNUM_RE .findall ((text or '').lower ())if w_p not in _EDGAR_STOPWORDS ]

        def _edgar_norm_form2 (form :str )->str :
            f_p =' '.join ((form or '').upper ().replace ('FORM',' ').split ())
            m_p =re .fullmatch ('(\\d{1,2})\\s*-?\\s*([A-Z])',f_p )
            if m_p :
                return f'{m_p.group(1)}-{m_p.group(2)}'
            m_p =re .fullmatch ('(DEF)\\s*-?\\s*(14A)',f_p )
            if m_p :
                return 'DEF 14A'
            return f_p 

        async def _pull_json (url :str ,cutoff :float ):
            cached_p =_EDGAR_CISTERN .get (url )
            if cached_p is not None :
                return cached_p 
            for _attempt_p in (0 ,1 ):
                remain =cutoff -monotonic ()
                if remain <12.0 :
                    return None 
                try :
                    bundle =await asyncio .wait_for (fetch_page (url ,provider =SCOUT_PROVIDER ,timeout =min (_EDGAR_PULL_LIMIT2_S ,remain -6.0 )),timeout =min (_EDGAR_PULL_LIMIT2_S ,remain -6.0 )+4.0 )
                except Exception :
                    continue 
                _burn_annotation (bundle )
                outcomes =list (getattr (bundle ,'results',None )or [])
                annotation =getattr (outcomes [0 ],'note',None )or ''if outcomes else ''
                start =annotation .find ('{')
                end =annotation .rfind ('}')
                if start ==-1 or end <=start :
                    continue 
                try :
                    obj_p =json .loads (annotation [start :end +1 ])
                except Exception :
                    continue 
                if isinstance (obj_p ,dict ):
                    _EDGAR_CISTERN [url ]=obj_p 
                    return obj_p 
            return None 

        def _edgar_select_submission (recent_p :dict ,form :str ,year :str ):
            forms_p =recent_p .get ('form')
            accs_p =recent_p .get ('accessionNumber')
            docs_p =recent_p .get ('primaryDocument')
            rdates_p =recent_p .get ('reportDate')
            fdates_p =recent_p .get ('filingDate')
            if not (isinstance (forms_p ,list )and isinstance (accs_p ,list )and isinstance (docs_p ,list )):
                return None 
            n_p =min (len (forms_p ),len (accs_p ),len (docs_p ))
            form2_norm =_edgar_norm_form2 (form )
            prime_year =None 
            prime_any =None 
            for i_p in range (n_p ):
                if _edgar_norm_form2 (str (forms_p [i_p ]))!=form2_norm :
                    continue 
                if accs_p [i_p ]is None or docs_p [i_p ]is None :
                    continue 
                acc_p =str (accs_p [i_p ])
                doc =str (docs_p [i_p ])
                if not acc_p or not (doc .endswith ('.htm')or doc .endswith ('.html')):
                    continue 
                rd_p =str (rdates_p [i_p ])if isinstance (rdates_p ,list )and i_p <len (rdates_p )and (rdates_p [i_p ]is not None )else ''
                fd_p =str (fdates_p [i_p ])if isinstance (fdates_p ,list )and i_p <len (fdates_p )and (fdates_p [i_p ]is not None )else ''
                key =rd_p or fd_p 
                if prime_any is None or key >prime_any [0 ]:
                    prime_any =(key ,acc_p ,doc )
                if year and rd_p [:4 ]==year :
                    if prime_year is None or key >prime_year [0 ]:
                        prime_year =(key ,acc_p ,doc )
            select =prime_year if year else prime_any 
            if select is None :
                return None 
            return (select [1 ],select [2 ])
        _EDGAR_SCOUT_HINT ='search "site:sec.gov {company} {year} {form}" and read_page the Archives result'

        async def _do_edgar_submission (company :str ,form :str ,year :str ,cutoff :float )->str :
            company =(company or '').strip ()
            form =(form or '').strip ()or '10-K'
            year =(year or '').strip ()[:4 ]
            hint_p =_EDGAR_SCOUT_HINT .format (company =company ,year =year ,form =form )
            if not company :
                return '# sec_filing: company required'
            if cutoff -monotonic ()<_EDGAR_LOWER_SLACK_S :
                return f'# sec_filing: skipped (low time) — {hint_p}'
            tickers_p =await _pull_json (_EDGAR_TICKERS_HREF ,cutoff )
            if not isinstance (tickers_p ,dict ):
                return f'# sec_filing: EDGAR ticker index unavailable — {hint_p}'
            want =_edgar_tokens (company )
            prime =None 
            for slot in tickers_p .values ():
                if not isinstance (slot ,dict ):
                    continue 
                title =str (slot .get ('title',''))
                ticker_p =str (slot .get ('ticker','')).lower ()
                words_p =set (_edgar_tokens (title ))
                n_hit_p =sum ((1 for w_p in want if w_p in words_p ))
                if len (want )==1 and ticker_p ==want [0 ]:
                    rating =100 
                elif want and n_hit_p ==len (want ):
                    rating =50 +n_hit_p 
                else :
                    continue 
                cand_p =(rating ,-len (title ),str (slot .get ('cik_str','')).zfill (10 ),title )
                if prime is None or cand_p >prime :
                    prime =cand_p 
            if prime is None :
                return f'# sec_filing({company!r}): no confident EDGAR match — {hint_p}'
            cik10 ,title =(prime [2 ],prime [3 ])
            subs_p =await _pull_json (_EDGAR_SUBMISSIONS_HREF .format (cik10 =cik10 ),cutoff )
            filings_p =subs_p .get ('filings')if isinstance (subs_p ,dict )else None 
            recent_p =filings_p .get ('recent')if isinstance (filings_p ,dict )else None 
            if not isinstance (recent_p ,dict ):
                return f'# sec_filing({company!r}): EDGAR submissions unavailable for {title} — {hint_p}'
            select =_edgar_select_submission (recent_p ,form ,year )
            if select is None :
                return f"# sec_filing({company!r}, {form!r}, year={year or 'latest'}): no matching filing in EDGAR's recent index for {title} — check the form/year, or {hint_p}"
            accession ,doc =select 
            url =_EDGAR_INSTRUMENT_HREF .format (cik =cik10 .lstrip ('0')or cik10 ,accession =accession .replace ('-',''),doc =doc )
            return f"# sec_filing -> {title} {form} {year or '(latest)'} primary document:\n{url}\nNow call read_page on this URL with a focus hint for the section you need, and cite figures from that read_page result."

        def _vault_folio2 (url :str ,vault :SpecimenVault )->tuple [int ,dict ]|None :
            u_p =(url or '').strip ().rstrip ('/')
            if not u_p :
                return None 
            for i_p in range (len (vault .rows )-1 ,-1 ,-1 ):
                slot =vault .rows [i_p ]
                if not slot .get ('text'):
                    continue 
                r_p =str (slot .get ('url')or '').rstrip ('/')
                if r_p ==u_p or r_p .endswith (u_p )or u_p .endswith (r_p ):
                    return (i_p +1 ,slot )
            return None 

        def _do_folio2_locate (url :str ,pattern_p :str ,vault :SpecimenVault )->str :
            hit_p =_vault_folio2 (url ,vault )
            if hit_p is None :
                return f'# page_grep: {url!r} has not been fetched this run; call read_page first'
            n_p ,slot =hit_p 
            text =slot .get ('text')or ''
            pat_p =(pattern_p or '').strip ()
            if not pat_p :
                return '# page_grep: empty pattern'
            try :
                rx_p =re .compile (pat_p ,re .I )
            except re .error :
                rx_p =re .compile (re .escape (pat_p ),re .I )
            out_p ,seen_at_p =([],[])
            for m_p in rx_p .finditer (text ):
                c_p =(m_p .start ()+m_p .end ())//2 
                if any ((abs (c_p -prev_p )<FOLIO2_LOCATE_PANE //2 for prev_p in seen_at_p )):
                    continue 
                seen_at_p .append (c_p )
                a_p =max (0 ,c_p -FOLIO2_LOCATE_PANE //2 )
                b_p =min (len (text ),a_p +FOLIO2_LOCATE_PANE )
                out_p .append (f'\n--- match @{a_p} ---\n{text[a_p:b_p]}')
                if len (out_p )>=FOLIO2_LOCATE_UPPER_HITS :
                    break 
            if not out_p :
                return f'# page_grep({pat_p!r}) on [{n_p}]: no match in {len(text)} chars. Try a shorter or looser pattern.'
            return f'# page_grep({pat_p!r}) on [{n_p}] -> {len(out_p)} match(es) of {len(text)} chars'+''.join (out_p )

        def _do_folio2_scan (url :str ,offset_p :int ,length_p :int ,vault :SpecimenVault )->str :
            hit_p =_vault_folio2 (url ,vault )
            if hit_p is None :
                return f'# page_read: {url!r} has not been fetched this run; call read_page first'
            n_p ,slot =hit_p 
            text =slot .get ('text')or ''
            a_p =max (0 ,min (int (offset_p or 0 ),max (0 ,len (text )-1 )))
            ln_p =int (length_p or FOLIO2_SCAN_UPPER_GLYPHS )
            b_p =min (len (text ),a_p +max (1 ,min (ln_p ,FOLIO2_SCAN_UPPER_GLYPHS )))
            return f'# page_read([{n_p}] @{a_p}:{b_p} of {len(text)})\n{text[a_p:b_p]}'

        def _do_pin_specimen (provenance :str ,citation2 :str ,vault :SpecimenVault )->str :
            crude =(provenance or '').strip ().strip ('[]')
            try :
                n_p =int (crude )
            except ValueError :
                return f'# retain_evidence: source must be a result number like [3], got {provenance!r}'
            if not 1 <=n_p <=len (vault .rows ):
                return f'# retain_evidence: no result [{n_p}] exists yet'
            slot =vault .rows [n_p -1 ]
            text =slot .get ('text')or ''
            q_p =(citation2 or '').strip ()
            if len (q_p )<PIN_LOWER_CITATION2 :
                return f'# retain_evidence: quote too short ({len(q_p)} chars); quote at least {PIN_LOWER_CITATION2} characters of the source text'
            if not text :
                return f'# retain_evidence: result [{n_p}] has no stored text to quote from'
            i_p =text .find (q_p )
            if i_p <0 :
                i_p =text .lower ().find (q_p .lower ())
            if i_p <0 :
                squashed_p =' '.join (q_p .split ())
                i_p =' '.join (text .split ()).lower ().find (squashed_p .lower ())
                if i_p >=0 :
                    i_p =-1 
            if i_p <0 :
                return f'# retain_evidence: that text does not appear in [{n_p}]. Quote it EXACTLY as the source prints it, or read more of the page first.'
            kept_p =slot .setdefault ('retained',[])
            if len (kept_p )>=PIN_UPPER_PER_SLOT :
                return f'# retain_evidence: [{n_p}] already has {len(kept_p)} retained excerpts'
            a_p =max (0 ,i_p -PIN_PAD_GLYPHS )
            b_p =min (int (slot .get ('note_len')or len (text )),i_p +len (q_p )+PIN_PAD_GLYPHS )
            if b_p <=a_p :
                return f'# retain_evidence: could not bound the excerpt in [{n_p}]'
            kept_p .append ((a_p ,b_p ))
            return f'# retain_evidence: kept {b_p - a_p} chars of [{n_p}] around your quote. Cite [{n_p}] for that claim.'

        async def _drive_implement (invoke ,query2 :str ,vault :SpecimenVault ,cutoff :float )->str :
            try :
                args_p =json .loads (getattr (invoke ,'arguments',None )or '{}')
            except Exception :
                args_p ={}
            if not isinstance (args_p ,dict ):
                args_p ={}
            name_p =getattr (invoke ,'name','')or ''
            if name_p =='web_search':
                return await _do_scout (str (args_p .get ('query')or ''),vault )
            if name_p =='read_page':
                return await _do_pull (str (args_p .get ('url')or ''),str (args_p .get ('focus')or ''),query2 ,vault )
            if name_p =='retain_evidence':
                return _do_pin_specimen (str (args_p .get ('source')or ''),str (args_p .get ('quote')or ''),vault )
            if name_p =='page_grep':
                return _do_folio2_locate (str (args_p .get ('url')or ''),str (args_p .get ('pattern')or ''),vault )
            if name_p =='page_read':
                return _do_folio2_scan (str (args_p .get ('url')or ''),args_p .get ('offset')or 0 ,args_p .get ('length')or FOLIO2_SCAN_UPPER_GLYPHS ,vault )
            if name_p =='sec_filing':
                return await _do_edgar_submission (str (args_p .get ('company')or ''),str (args_p .get ('form')or ''),str (args_p .get ('year')or ''),cutoff )
            return f'# unknown tool {name_p!r}'
        _REASONING_OBLIGATORY =('Qwen/Qwen3.6',)

        def _minimal_deliberate (track :str ,model :str ='')->dict :
            for prefix_p in _REASONING_OBLIGATORY :
                if model .startswith (prefix_p ):
                    return {'enabled':True ,'effort':'low'}
            return {'enabled':False }

        async def _dialogue_bare (track :str ,model :str ,system_p :str ,user_p :str ,*,max_tokens :int ,timeout :float ,think :dict |None =None )->str :
            if think is None :
                think =_minimal_deliberate (track ,model )
            bundle =await llm_chat (provider =track ,model =model ,messages =[{'role':'system','content':system_p },{'role':'user','content':user_p }],temperature =0.15 ,max_output_tokens =max_tokens ,timeout =timeout ,thinking =think )
            _burn_annotation (bundle )
            llm_p =getattr (bundle ,'llm',None )
            text =(getattr (llm_p ,'raw_text',None )or '').strip ()
            if text :
                return text 
            choices_p =getattr (llm_p ,'choices',None )or []
            if choices_p :
                content_p =getattr (choices_p [0 ].message ,'content',None )
                if isinstance (content_p ,str ):
                    return content_p .strip ()
            return ''

        async def _dialogue_tick (messages :list [dict ],cutoff :float ,*,finish_only :bool ,force_tools :bool =False ):
            for track_model in ((LLM_TRACK_A ,ORBIT_MODEL_A ),(LLM_TRACK_B ,ORBIT_MODEL_B )):
                track =track_model [0 ]
                model =track_model [1 ]
                timeout =min (TICK_LIMIT2_S ,cutoff -monotonic ()-5.0 )
                if timeout <=5.0 :
                    return None 
                try :
                    bundle =await llm_chat (provider =track ,model =model ,messages =messages ,tools =ORBIT_IMPLEMENTS if force_tools or not finish_only else None ,tool_choice ='auto'if force_tools or not finish_only else None ,temperature =0.2 ,thinking ={'enabled':False }if finish_only and track ==LLM_TRACK_B else {'enabled':True ,'effort':'low'},max_output_tokens =6000 if finish_only and track ==LLM_TRACK_B else None ,timeout =timeout )
                    _burn_annotation (bundle )
                    return bundle 
                except Exception :
                    continue 
            return None 

        async def _knowledge_dossier (query2 :str )->tuple [str ,str ]:
            system_p ='Senior research analyst. Commit to concrete best answers from knowledge; mark uncertain values (verify). Never refuse.'
            user_p =f"Question:\n{query2}\n\nFill in this internal worksheet. It is planning scratch for your own use, never an answer, so keep the tags lowercase and never reuse them as section headings later.\ndraft: your full best answer now — candidate pool, every stated condition applied, qualifying entities with figures/dates, near-miss exclusions. Flag shaky facts with (verify).\nconditions: each atomic condition in the question, numbered, including any output-format demand.\nsearches: 3-6 precise web searches for the facts that decide the answer (entity + metric + year; include a named source's site: filter).\nurls: up to 5 exact URLs worth reading directly (official stats pages, sec.gov Archives filings, boxofficemojo year pages); 'none' if unsure."
            crude =''
            try :
                crude =await _dialogue_bare (LLM_TRACK_A ,ORBIT_MODEL_A ,system_p ,user_p ,max_tokens =2400 ,timeout =DOSSIER_LIMIT2_S ,think =_minimal_deliberate (LLM_TRACK_A ,ORBIT_MODEL_A ))
            except Exception :
                try :
                    crude =await _dialogue_bare (LLM_TRACK_B ,ORBIT_MODEL_B ,system_p ,user_p ,max_tokens =2400 ,timeout =DOSSIER_LIMIT2_S ,think =_minimal_deliberate (LLM_TRACK_B ,ORBIT_MODEL_B ))
                except Exception :
                    crude =''
            if not crude :
                return ('','')
            rough =crude 
            cut_p =min ((mm_p .start ()for mm_p in (re .search ('[#*_\\s]*(?:conditions|CHECKLIST)[#*_\\s]*:',crude ,re .IGNORECASE ),re .search ('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:conditions|CHECKLIST)[ \\t]*[#*_]{0,3}[ \\t]*$',crude ,re .IGNORECASE |re .MULTILINE ))if mm_p is not None ),default =None )
            if cut_p is not None :
                rough =crude [:cut_p ]
            rough =re .sub ('^[#*_\\s]*(?:draft|BEST ANSWER)[#*_\\s]*:[#*_\\s]*','',rough ,flags =re .IGNORECASE )
            rough =re .sub ('^[ \\t]*[#*_>]{0,4}[ \\t]*(?:draft|BEST ANSWER)[ \\t]*[#*_]{0,3}[ \\t]*\\n+','',rough ,flags =re .IGNORECASE )
            rough =rough .strip ()
            dossier ='PRIOR ANALYSIS — your own planning worksheet (verify anything marked (verify), and correct it wherever tool results disagree). Its tags are internal: never reproduce them, or any section named after them, in the answer.\n'+crude .strip ()
            return (rough ,dossier )
        _SOW_TOKEN_RE =re .compile ("[A-Za-z0-9][A-Za-z0-9.\\-']+")
        _SOW_STOP =frozenset ('name list give tell show find identify please could would you your can may might should must let make sure both also'.split ())
        UPPER_SOW_QUERIES =3 

        def _sow_queries (query2 :str ,ensemble_query2 :bool )->list [str ]:
            q_p =' '.join ((query2 or '').split ())
            if not q_p :
                return []
            seeds_p =[q_p [:300 ]]
            salient_p =[t_p for t_p in _SOW_TOKEN_RE .findall (q_p )if len (t_p )>=3 and t_p .lower ()not in _STOP_P and (t_p .lower ()not in _SOW_STOP )]
            if len (salient_p )>=2 :
                seeds_p .append (' '.join (salient_p [:8 ]))
            if ensemble_query2 and salient_p :
                seeds_p .append ('list of '+' '.join (salient_p [:6 ]))
            try:
                for name in _named_origins_h(query2)[:1]:
                    site = _origin_site_h(name)
                    focus = ' '.join(salient_p[:6])
                    if site and '.' in site:
                        seeds_p.insert(1, f'site:{site} {focus}'.strip())
                    else:
                        seeds_p.insert(1, f'{name} {focus}'.strip())
            except Exception:
                pass
            out_p :list [str ]=[]
            for s_p in seeds_p :
                s_p =s_p .strip ()
                if s_p and s_p not in out_p :
                    out_p .append (s_p )
            return out_p [:UPPER_SOW_QUERIES ]

        async def _presow (query2 :str ,ensemble_query2 :bool ,vault :SpecimenVault ,cutoff :float )->str :
            seeds_p =_sow_queries (query2 ,ensemble_query2 )
            if not seeds_p or cutoff -monotonic ()<40.0 :
                return ''
            slabs :list =[]
            for sow in seeds_p :
                if cutoff -monotonic ()<30.0 :
                    break 
                try :
                    out_p =await asyncio .wait_for (_do_scout (sow ,vault ),timeout =SCOUT_LIMIT2_S *2 +6.0 )
                    slabs .append (_seal_implement_emission (out_p ,vault ))
                except Exception :
                    continue 
            good_p =[b_p for b_p in slabs if isinstance (b_p ,str )and _TAG_MARK_RE .search (b_p )]
            if not good_p :
                return ''
            return 'Automatic first-pass searches (already numbered — cite these [n] directly, and search further as needed):\n\n'+'\n'.join (good_p )
        TABLEAU_SLOT_GLYPHS =260 
        TABLEAU_SEAL_GLYPHS =1200 
        TABLEAU_UPPER_SLOTS =48 
        _FOLDED_P ='[folded into the evidence board]'

        def _tableau_slots (vault :SpecimenVault ,query2 :str )->list [tuple [int ,int ,str ]]:
            rows :list [tuple [int ,int ,str ]]=[]
            for catalogue ,slot in enumerate (vault .rows ,start =1 ):
                if slot .get ('kind')=='reserved':
                    continue 
                preview =' '.join ((slot .get ('preview')or '').split ())
                if not preview :
                    continue 
                rank_p =_provenance_rank (slot .get ('url',''),slot .get ('title',''),preview ,query2 )
                title =' '.join ((slot .get ('title')or '').split ())[:90 ]
                rows .append ((rank_p ,catalogue ,'[%d] %s — %s'%(catalogue ,title ,preview [:TABLEAU_SLOT_GLYPHS ])))
            rows .sort (key =lambda r_p :(r_p [0 ],r_p [1 ]))
            return rows [:TABLEAU_UPPER_SLOTS ]

        def _paint_tableau (vault :SpecimenVault ,query2 :str ,*,width_p :int =TABLEAU_SLOT_GLYPHS ,char_cap :int =18000 )->str :
            scored_p =[]
            for catalogue ,slot in enumerate (vault .rows ,start =1 ):
                if slot .get ('kind')=='reserved':
                    continue 
                preview =' '.join ((slot .get ('preview')or '').split ())
                if not preview :
                    continue 
                rank_p =_provenance_rank (slot .get ('url',''),slot .get ('title',''),preview ,query2 )
                scored_p .append ((rank_p ,catalogue ,slot ,preview ))
            scored_p .sort (key =lambda r_p :(r_p [0 ],r_p [1 ]))
            parts_p ,spent_p =([],0 )
            for _rank_p ,catalogue ,slot ,preview in scored_p [:TABLEAU_UPPER_SLOTS ]:
                title =' '.join ((slot .get ('title')or '').split ())[:90 ]
                slab ='[%d] %s (%s)\n%s'%(catalogue ,title ,slot .get ('url')or '',preview [:width_p ])
                if spent_p +len (slab )>char_cap :
                    break 
                spent_p +=len (slab )
                parts_p .append (slab )
            if not parts_p :
                return ''
            return 'EVIDENCE BOARD — every item gathered so far, strongest source first. These [n] are the citations available to you; cite the one that actually states each fact, never the same [n] for everything.\n\n'+'\n\n'.join (parts_p )

        def _fold_transcript_p (messages :list [dict ],vault :SpecimenVault ,query2 :str )->None :
            implement_positions =[i_p for i_p ,m_p in enumerate (messages )if isinstance (m_p ,dict )and m_p .get ('role')=='tool']
            for i_p in implement_positions [:-8 ]:
                if messages [i_p ].get ('content')!=_FOLDED_P :
                    messages [i_p ]=dict (messages [i_p ])
                    messages [i_p ]['content']=_FOLDED_P 
            tableau =_paint_tableau (vault ,query2 )
            if not tableau :
                return 
            for i_p ,m_p in enumerate (messages ):
                if isinstance (m_p ,dict )and m_p .get ('role')=='system'and str (m_p .get ('content','')).startswith ('EVIDENCE BOARD'):
                    messages [i_p ]={'role':'system','content':tableau }
                    return 
            messages .append ({'role':'system','content':tableau })

        async def _orbit (query2 :str ,dossier :str ,vault :SpecimenVault ,cutoff :float ,tick_lid :int ,carry :list [dict ]|None =None ,allow_tools_in_wrapup :bool =False )->tuple [str ,list [dict ]]:
            if carry is not None :
                messages =carry 
            else :
                ensemble_q =_needs_ensemble_fullness (query2 )
                messages =[{'role':'system','content':ORBIT_STATUTE }]
                if ensemble_q :
                    messages .append ({'role':'system','content':ENSEMBLE_STATUTE2 })
                if _needs_apex_proof (query2 ):
                    messages .append ({'role':'system','content':APEX_STATUTE2 })
                try:
                    _onames = _named_origins_h(query2)
                    if _onames:
                        messages.append({'role': 'system', 'content': _origin_edict_h(_onames)})
                except Exception:
                    pass
                if dossier :
                    messages .append ({'role':'system','content':dossier })
                seeded_p =await _presow (query2 ,ensemble_q ,vault ,cutoff )
                if seeded_p :
                    messages .append ({'role':'system','content':seeded_p })
                messages .append ({'role':'user','content':query2 })
            verdictp =''
            ordered_finale =False 
            repairs_remain =VERDICT_REWORK_TICKS 
            for tick in range (1 ,tick_lid +1 ):
                remain =cutoff -monotonic ()
                if remain <=LOWER_REMAINDER_S :
                    break 
                out_of_time_p =remain <=FINALE_AT_S 
                out_of_burn =_burn_remain ()<=FINALE_LOWER_USD 
                finish_only =out_of_time_p or out_of_burn or tick >=tick_lid 
                if (finish_only or tick >=tick_lid -1 )and (not ordered_finale ):
                    messages .append ({'role':'system','content':_finale_edict (remain )})
                    ordered_finale =True 
                bundle =await _dialogue_tick (messages ,cutoff ,finish_only =finish_only ,force_tools =allow_tools_in_wrapup and tick ==1 )
                if bundle is None :
                    break 
                llm_p =getattr (bundle ,'llm',None )
                choices_p =getattr (llm_p ,'choices',None )or []
                if not choices_p :
                    break 
                msg_p =choices_p [0 ].message 
                invokes =getattr (msg_p ,'tool_calls',None )or ()
                if not invokes :
                    nominee =(getattr (llm_p ,'raw_text',None )or '').strip ()
                    if not nominee :
                        content_p =getattr (msg_p ,'content',None )
                        if isinstance (content_p ,str ):
                            nominee =content_p .strip ()
                    if not _is_viable_verdict (nominee ):
                        if repairs_remain >0 and cutoff -monotonic ()>LOWER_REMAINDER_S +10.0 :
                            repairs_remain -=1 
                            messages .append ({'role':'system','content':_REWORK_EDICT })
                            verdictp =''
                            continue 
                        verdictp =''
                        break 
                    verdictp =nominee 
                    messages .append ({'role':'assistant','content':verdictp })
                    break 
                messages .append (msg_p .to_input_message ())
                drive_invokes =invokes [:8 ]
                implement_ration =max (5.0 ,min (PULL_LIMIT2_S *2 +6.0 ,cutoff -monotonic ()-LOWER_REMAINDER_S ))
                implement_tasks =[asyncio .ensure_future (_drive_implement (c_p ,query2 ,vault ,cutoff ))for c_p in drive_invokes ]
                try :
                    await asyncio .wait (implement_tasks ,timeout =implement_ration )
                except Exception :
                    pass 
                outcomes =[]
                for t_p in implement_tasks :
                    if t_p .done ():
                        try :
                            outcomes .append (t_p .result ())
                        except Exception as exc_p :
                            outcomes .append (f'# tool crashed: {exc_p}')
                    else :
                        t_p .cancel ()
                        outcomes .append ('# tool timed out — use what you already have')
                for invoke_outcome in zip (drive_invokes ,outcomes ):
                    invoke =invoke_outcome [0 ]
                    body_p =_seal_implement_emission (invoke_outcome [1 ],vault )
                    messages .append ({'role':'tool','tool_call_id':invoke .id ,'content':body_p })
                for invoke in invokes [8 :]:
                    messages .append ({'role':'tool','tool_call_id':invoke .id ,'content':'# skipped: per-turn tool budget reached — re-issue next turn if still needed'})
                _fold_transcript_p (messages ,vault ,query2 )
            return (verdictp ,messages )

        async def _inspect_splice (query2 :str ,verdictp :str ,messages :list [dict ],vault :SpecimenVault ,cutoff :float )->str :
            sounding =f"""Audit this answer vs the question. JSON only. Keys:
"unanswered_parts" (list; question elements not addressed),
"uncited_facts" (list; load-bearing claims without [n]),
"wrong_kind" (list; named entity is the wrong KIND — person vs series, duo vs show),
"incomplete_roster" (list; THE MOST COMMON LOSS. If the question ranges over a candidate pool — a closed set that can be enumerated, or several conditions applied to a class — then: is the pool itself stated and plausibly COMPLETE, and does the answer give a verdict for EVERY member (qualifies / excluded because X, each cited)? Name any pool member the answer never mentions, and say so if the pool looks truncated — an answer naming 3 qualifiers when the pool holds 6 scores as WRONG, not partial),
"thin_proof" (list; a qualifier lacking a per-condition citation, or a plausible near-miss candidate never addressed),
"hand_waved_tally" (list; for a superlative/count/most-common question: the answer asserts a winner or a count WITHOUT showing the candidate table it was derived from. Phrases like 'among others', 'and several more', 'multiple X', or naming 2 examples to justify a count are all hand-waving — say so and name what the tally must list).
Empty lists when clean.

Question:
{query2}

Answer:
{verdictp[:11000]}"""
            try :
                crude =await _dialogue_bare (LLM_TRACK_A ,INSPECT_MODEL ,'Strict completeness auditor. JSON only.',sounding ,max_tokens =2200 ,timeout =max (8.0 ,min (INSPECT_LIMIT2_S ,cutoff -monotonic ()-72.0 )))
                crude =re .sub ('^```(?:json)?\\s*|\\s*```$','',crude .strip (),flags =re .I |re .M )
                report_p =json .loads (crude )
            except Exception :
                return verdictp 
            voids :list [str ]=[]
            rollcall_voids :list [str ]=[]
            if isinstance (report_p ,dict ):
                for key in ('incomplete_roster','hand_waved_tally','unanswered_parts','uncited_facts','wrong_kind','thin_proof'):
                    vals_p =report_p .get (key )
                    if isinstance (vals_p ,list ):
                        found_p =[str (v_p )for v_p in vals_p if str (v_p ).strip ()]
                        if key in ('incomplete_roster','hand_waved_tally'):
                            rollcall_voids .extend (found_p )
                        voids .extend (found_p )
            if not voids or cutoff -monotonic ()<70.0 :
                return verdictp 
            edict ='AUDIT: the answer has gaps:\n- '+'\n- '.join (voids [:6 ])
            if rollcall_voids :
                edict +="\nThe candidate pool is incomplete — this loses outright. FIRST search for the authoritative LIST/roster/table that enumerates the whole pool (query it as a list, e.g. '<pool subject> full list', not one member at a time), verify EVERY member against every condition, then rewrite."
            edict +='\nUse at most 3 tool calls to close the most important gaps, then rewrite the COMPLETE final answer with [n] citations in the required shape.'
            messages .append ({'role':'system','content':edict })
            patched_p ,_ =await _orbit (query2 ,'',vault ,cutoff ,INSPECT_SURPLUS_TICKS +1 ,carry =messages ,allow_tools_in_wrapup =True )
            patched_p =patched_p .strip ()
            if not _is_viable_verdict (patched_p )or len (patched_p )<int (len (verdictp )*0.6 ):
                return verdictp 
            return patched_p 
        _BRACE_FIX ={12304 :'[',12305 :']',65339 :'[',65341 :']',65288 :'(',65289 :')',8209 :'-',8722 :'-'}
        for _d_p in range (10 ):
            _BRACE_FIX [65296 +_d_p ]=chr (48 +_d_p )

        def _canonize_braces (text :str )->str :
            return (text or '').translate (_BRACE_FIX )
        _TAG_NUM_RE =re .compile ('\\[([0-9][0-9,\\s\\-]*)\\]')

        def _tagged_indexes2 (verdictp :str ,top_p :int )->list [int ]:
            verdictp =_canonize_braces (verdictp )
            seen_p :set [int ]=set ()
            out_p :list [int ]=[]
            for m_p in _TAG_NUM_RE .finditer (verdictp ):
                for chunk_p in m_p .group (1 ).split (','):
                    piece_p =chunk_p .strip ()
                    reach =re .fullmatch ('(\\d{1,4})\\s*-\\s*(\\d{1,4})',piece_p )
                    if reach :
                        lo_p =int (reach .group (1 ))
                        hi_p =int (reach .group (2 ))
                        for n_p in range (lo_p ,min (hi_p ,lo_p +16 )+1 ):
                            if 1 <=n_p <=top_p and n_p not in seen_p :
                                seen_p .add (n_p )
                                out_p .append (n_p )
                    elif piece_p .isdigit ():
                        n_p =int (piece_p )
                        if 1 <=n_p <=top_p and n_p not in seen_p :
                            seen_p .add (n_p )
                            out_p .append (n_p )
            return out_p 
        _EMISSION_ONLY_RE =re .compile ('\\boutput only\\b|\\brespond with only\\b|\\breply with only\\b|\\banswer with only\\b|\\bonly the exact\\b|\\bnothing else\\b|\\bno explanation\\b|\\bwithout explanation\\b|\\bno other text\\b|\\bjust the (?:name|names|value|values|number|numbers|list|text|answer|title|titles)\\b',re .IGNORECASE )
        _EMISSION_ONLY_LOWER_GLYPHS =2 

        def _verdict_line_only (verdictp :str ,query2 :str )->str :
            if not verdictp or not _EMISSION_ONLY_RE .search (query2 or ''):
                return verdictp 
            for crude in verdictp .split ('\n'):
                stripped_p =crude .strip ()
                if not stripped_p :
                    continue 
                if stripped_p [0 ]in '#>':
                    continue 
                line_p =re .sub ('^[*_`\\s]+|[*_`\\s]+$','',stripped_p ).strip ()
                if not line_p :
                    continue 
                if line_p .startswith ('|')or line_p .endswith (':'):
                    continue 
                if line_p .count ('|')>=3 :
                    continue 
                if len (line_p )>=_EMISSION_ONLY_LOWER_GLYPHS :
                    return line_p 
            return verdictp 
        _GLOSS_RE_P =re .compile ('^(?P<a>[^()]{2,60}?)\\s*\\((?P<b>[^()]{2,60})\\)$')

        def _verbatim_from_provenance (value_p :str ,vault :SpecimenVault )->str :
            v_p =(value_p or '').strip ()
            m_p =_GLOSS_RE_P .match (v_p )
            if not m_p :
                return value_p 
            texts_p =[r_p .get ('text')or ''for r_p in vault .rows if r_p .get ('text')]
            if not texts_p :
                return value_p 

            def seen_p (t_p :str )->bool :
                return bool (t_p )and any ((t_p in src_p for src_p in texts_p ))
            if seen_p (v_p ):
                return value_p 
            a_p ,b_p =(m_p .group ('a').strip (),m_p .group ('b').strip ())
            hits_p =[x_p for x_p in (b_p ,a_p )if seen_p (x_p )]
            if len (hits_p )==1 :
                return hits_p [0 ]
            if len (hits_p )==2 :
                lo_p ,hi_p =sorted (hits_p ,key =len )
                if lo_p .lower ()in hi_p .lower ():
                    return hi_p 
            return value_p 

        def _verbatim_structured_p (obj_p ,vault :SpecimenVault ,depth_p :int =0 ):
            if depth_p >6 :
                return obj_p 
            if isinstance (obj_p ,str ):
                return _verbatim_from_provenance (obj_p ,vault )
            if isinstance (obj_p ,list ):
                return [_verbatim_structured_p (x_p ,vault ,depth_p +1 )for x_p in obj_p ]
            if isinstance (obj_p ,dict ):
                return {k :_verbatim_structured_p (v_p ,vault ,depth_p +1 )for k ,v_p in obj_p .items ()}
            return obj_p 

        def _footnotes_for (verdictp :str ,vault :SpecimenVault )->list [CitationRef ]:
            refs_p :list [CitationRef ]=[]
            spent_p =0 
            for n_p in _tagged_indexes2 (verdictp ,len (vault .rows )):
                if len (refs_p )>=FOOTNOTE_LID :
                    break 
                ref =vault .ref_for (n_p )
                if ref is None :
                    continue 
                slot =vault .rows [n_p -1 ]
                slices =getattr (ref ,'slices',None )
                cost =sum ((max (0 ,s_p .end -s_p .start )for s_p in slices ))if slices else int (slot .get ('note_len')or 0 )
                if spent_p +cost >SPECIMEN_GLYPH_RATION :
                    continue 
                spent_p +=cost 
                refs_p .append (ref )
            return refs_p 
        _VOUCH_MARK_RE =re .compile ('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)',re .I )
        _IMPLEMENT_MARKUP_RE =re .compile ('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url|\\bsec_filing\\s*[（(]\\s*company',re .I )
        _STUB2_VERDICT_RE =re .compile ('^\\s*(?:best-effort answer unavailable|no question provided)',re .I )
        _REFUSAL_ONLY_RE_P =re .compile ("^\\s*(?:i (?:cannot|can't|am unable|was unable)|unable to|sorry[,.]|i don'?t have (?:enough|access))",re .I )
        _INTENT_MONOLOGUE_RE =re .compile ("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,? (?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check))",re .I )
        LOWER_VERDICT_GLYPHS =40 
        LOWER_TAGGED_VERDICT_GLYPHS =12 
        _TAG_MARK_RE =re .compile ('\\[[0-9]{1,3}\\]')

        def _looks_like_implement_json (s_p :str )->bool :
            return bool (re .match ('\\s*\\{\\s*"(?:name|tool|function)"\\s*:',s_p ))

        def _is_degenerate_repetition_p (text :str )->bool :
            body_p =text or ''
            lines_p =[ln_p .strip ().lower ()for ln_p in body_p .split ('\n')if len (ln_p .strip ())>25 ]
            if len (lines_p )>=3 :
                for ln_p in set (lines_p ):
                    if lines_p .count (ln_p )>=3 :
                        return True 
                if len (set (lines_p ))*2 >len (lines_p ):
                    return False 
            sents_p =[s_p .strip ().lower ()for s_p in re .split ('(?<=[.!?])\\s+|\\n+',body_p )if len (s_p .strip ())>25 ]
            if len (sents_p )<3 :
                return False 
            uniq_p =set (sents_p )
            if len (uniq_p )*2 <=len (sents_p ):
                return True 
            for s_p in uniq_p :
                if sents_p .count (s_p )>=3 :
                    return True 
            return False 

        def _is_viable_verdict (text :str )->bool :
            s_p =_canonize_braces (text ).strip ()
            if not s_p :
                return False 
            if _IMPLEMENT_MARKUP_RE .search (s_p )or _looks_like_implement_json (s_p ):
                return False 
            if _STUB2_VERDICT_RE .match (s_p )or _is_degenerate_repetition_p (s_p ):
                return False 
            tagged =bool (_TAG_MARK_RE .search (s_p ))
            if tagged and len (s_p )>=LOWER_TAGGED_VERDICT_GLYPHS :
                return True 
            if len (s_p )<LOWER_VERDICT_GLYPHS :
                return False 
            if len (s_p )<400 and (_REFUSAL_ONLY_RE_P .match (s_p )or _INTENT_MONOLOGUE_RE .match (s_p )):
                return False 
            return True 
        _SEAL_STATUTE ="You are writing the FINAL ANSWER to a research question from evidence that has already been gathered. You have NO tools and must not invent new lookups. Use only the evidence board below plus clearly stated general knowledge. Sentence one is the direct answer in the requested shape; then the proof with [n] citations drawn from the board. Pin premises the question names. Never narrate missing evidence; never write uncertainty markers. If a set or superlative is asked, keep the comparison / membership table in the proof."
        _REWORK_EDICT ='Your last message was not a usable final answer (it contained tool-call markup, was empty, or was a refusal). Do NOT emit tool syntax as text. Write the FINAL ANSWER now as plain prose: first words are the answer entities themselves, every factual claim followed by its [n] citation, then the short proof section. Nothing else.'

        def _sterilize_rough (text :str )->str :
            return _VOUCH_MARK_RE .sub ('',text or '').strip ()

        def _vault_breviary (vault :SpecimenVault ,char_cap :int =60000 )->str :
            parts_p :list [str ]=[]
            spent_p =0 
            for i_p ,slot in enumerate (vault .rows ,start =1 ):
                text =(slot .get ('preview')or '').strip ()
                if not text :
                    continue 
                slab =f"[{i_p}] {slot.get('title') or ''} ({slot.get('url') or ''})\n{text}"
                if spent_p +len (slab )>char_cap :
                    break 
                spent_p +=len (slab )
                parts_p .append (slab )
            return '\n\n'.join (parts_p )
        _FURNITURE_RE_P =re .compile ('^\\s*(?:share|search|home|menu|subscribe|sign\\s*in|log\\s*in|newsletter|advertisement|cookie|skip to|follow us|read more|related|tags?|categories?|privacy|terms|contact|about us|navigation|toggle)\\b',re .I )
        _SRC_FOOTNOTE_RE_P =re .compile ('\\[\\s*\\d{1,3}\\s*\\]')
        _MD_LINK_RE_P =re .compile ('\\]\\(')
        _BARE_HREF_RE =re .compile ('(?<!\\]\\()https?://')
        _SENTENCEY_RE_P =re .compile ('[.!?]\\s|[.!?]$|\\b(?:is|was|were|are|has|have|had|reported|announced|released|won|ranked|totall?ed)\\b',re .I )

        def _substantive_opener (preview :str ,limit_p :int =280 )->str :
            kept_p :list [str ]=[]
            broke_p =False 
            for chunk_p in re .split ('(?<=[.!?])\\s+|\\n+',_SRC_FOOTNOTE_RE_P .sub ('',preview or '')):
                seg_p =' '.join (chunk_p .split ())
                if len (seg_p )<30 or len (seg_p )>400 :
                    if kept_p :
                        broke_p =True 
                        break 
                    continue 
                if _SENTENCEY_RE_P .search (seg_p )is None :
                    if kept_p :
                        broke_p =True 
                        break 
                    continue 
                if _FURNITURE_RE_P .match (seg_p )and (not re .search ('\\d',seg_p )):
                    if kept_p :
                        broke_p =True 
                        break 
                    continue 
                if seg_p .startswith (('*','|','↑','#')):
                    if kept_p :
                        broke_p =True 
                        break 
                    continue 
                links_p =len (_MD_LINK_RE_P .findall (seg_p ))+len (_BARE_HREF_RE .findall (seg_p ))
                if links_p and links_p *110 >=len (seg_p ):
                    if kept_p :
                        broke_p =True 
                        break 
                    continue 
                kept_p .append (seg_p )
                if sum ((len (k )for k in kept_p ))>=limit_p :
                    break 
            else :
                pass 
            out_p =' '.join (kept_p ).strip ()
            if len (out_p )>limit_p :
                cut_p =out_p .rfind (' ',0 ,limit_p )
                out_p =out_p [:cut_p if cut_p >60 else limit_p ].rstrip (' ,;:-')
            return out_p 

        def _mechanical_verdict (query2 :str ,vault :SpecimenVault )->str :
            rows =[(i_p ,r_p )for i_p ,r_p in enumerate (vault .rows ,start =1 )if (r_p .get ('preview')or '').strip ()]
            if not rows :
                return ''
            out_p =['Best-supported findings from the sources retrieved:']
            picked_p =0 
            for i_p ,r_p in rows :
                if picked_p >=6 :
                    break 
                openerp =_substantive_opener (r_p .get ('preview')or '')
                if not openerp :
                    continue 
                title =(r_p .get ('title')or '').strip ()
                out_p .append (f"- {(title + ': ' if title else '')}{openerp} [{i_p}]")
                picked_p +=1 
            if picked_p ==0 :
                for i_p ,r_p in rows [:4 ]:
                    openerp =' '.join ((r_p .get ('preview')or '').split ())[:280 ]
                    if openerp :
                        out_p .append (f'- {openerp} [{i_p}]')
                if len (out_p )==1 :
                    return ''
            return '\n'.join (out_p )

        async def _inscribe_from_breviary (query2 :str ,vault :SpecimenVault ,cutoff :float )->str :
            remain =cutoff -monotonic ()
            if remain <14.0 :
                return ''
            breviary =_vault_breviary (vault )
            if not breviary :
                return ''
            convo_p =[{'role':'system','content':_SEAL_STATUTE },{'role':'user','content':f'Question: {query2}\n\nNumbered evidence you gathered (cite facts by these [n]):\n\n{breviary}\n\nWrite the FINAL ANSWER now from this evidence. Plain prose, no tool syntax. First words are the answer entities; every factual claim carries its [n]; then the short proof section (pool, conditions, qualifiers, exclusions).'}]

            async def _one_p (track :str ,model :str ,ration :float )->str :
                bundle =await llm_chat (provider =track ,model =model ,messages =convo_p ,temperature =0.15 ,max_output_tokens =2600 ,timeout =ration ,thinking =_minimal_deliberate (track ,model ))
                _burn_annotation (bundle )
                llm_p =getattr (bundle ,'llm',None )
                text =(getattr (llm_p ,'raw_text',None )or '').strip ()
                if not text :
                    choices_p =getattr (llm_p ,'choices',None )or []
                    if choices_p :
                        c_p =getattr (choices_p [0 ].message ,'content',None )
                        if isinstance (c_p ,str ):
                            text =c_p .strip ()
                return text 
            lanes_p =((LLM_TRACK_A ,ORBIT_MODEL_A ),(LLM_TRACK_B ,ORBIT_MODEL_B ))
            for i_p ,track_model in enumerate (lanes_p ):
                remain =cutoff -monotonic ()
                if remain <14.0 :
                    return ''
                ration =min (RECOVER_LIMIT2_S ,remain -BREVIARY_REMAINDER_S )
                if i_p ==0 :
                    ration =min (ration ,max (12.0 ,remain -14.0 -BREVIARY_REMAINDER_S ))
                if ration <8.0 :
                    return ''
                try :
                    text =await _one_p (track_model [0 ],track_model [1 ],ration )
                except Exception :
                    continue 
                if _is_viable_verdict (text ):
                    return text 
            return ''

        async def _knowledge_fallback2 (query2 :str ,cutoff :float )->str :
            remain =cutoff -monotonic ()
            if remain <12.0 :
                return ''
            try :
                return await _dialogue_bare (LLM_TRACK_A ,FALLBACK2_MODEL ,'Expert researcher. Best definitive answer with concrete entities, numbers, dates. Never refuse.',query2 ,max_tokens =2600 ,timeout =min (45.0 ,remain -4.0 ))
            except Exception :
                return ''

        async def _outline2_emission (query2 :str ,verdictp :str ,outline2 ,cutoff :float )->object |None :
            ask_p =f'Convert the answer to a JSON value valid under the schema. Output ONLY the JSON value.\n\nSchema:\n{json.dumps(outline2)}\n\nQuestion:\n{query2}\n\nAnswer:\n{verdictp[:14000]}'
            for track ,model in ((LLM_TRACK_A ,OUTLINE2_MODEL ),(LLM_TRACK_A ,FALLBACK2_MODEL ),(LLM_TRACK_B ,ORBIT_MODEL_B )):
                remain =cutoff -monotonic ()
                if remain <12.0 :
                    break 
                try :
                    crude =await _dialogue_bare (track ,model ,'You output strictly valid JSON.',ask_p ,max_tokens =3400 ,timeout =min (45.0 ,remain -4.0 ))
                    crude =re .sub ('^```(?:json)?\\s*|\\s*```$','',crude .strip (),flags =re .I |re .M ).strip ()
                    value_p =json .loads (crude )
                    if _matches_outline2_contour (value_p ,outline2 ):
                        return value_p 
                    if isinstance (value_p ,dict )and len (value_p )==1 :
                        inner_p =list (value_p .values ())[0 ]
                        if _matches_outline2_contour (inner_p ,outline2 ):
                            return inner_p 
                except Exception :
                    continue 
            return None 

        def _outline2_variety (outline2 )->str :
            if not isinstance (outline2 ,dict ):
                return ''
            kind =outline2 .get ('type')
            if isinstance (kind ,list ):
                kind =kind [0 ]if kind else None 
            if kind is None :
                for key in ('anyOf','oneOf','allOf'):
                    branch_p =outline2 .get (key )
                    if isinstance (branch_p ,list ):
                        for sub in branch_p :
                            got_p =_outline2_variety (sub )
                            if got_p :
                                return got_p 
                if isinstance (outline2 .get ('properties'),dict ):
                    return 'object'
                if isinstance (outline2 .get ('enum'),list ):
                    return 'string'
                return ''
            return str (kind )

        def _matches_outline2_contour (value_p ,outline2 )->bool :
            kind =_outline2_variety (outline2 )
            if not kind :
                return True 
            if kind =='array':
                return isinstance (value_p ,list )
            if kind =='object':
                return isinstance (value_p ,dict )
            if kind =='string':
                return isinstance (value_p ,str )
            if kind =='integer':
                return isinstance (value_p ,int )and (not isinstance (value_p ,bool ))
            if kind =='number':
                return isinstance (value_p ,(int ,float ))and (not isinstance (value_p ,bool ))
            if kind =='boolean':
                return isinstance (value_p ,bool )
            if kind =='null':
                return value_p is None 
            return True 
        _NUM_IN_TEXT_RE_P =re .compile ('-?\\d[\\d,]*(?:\\.\\d+)?')

        def _force2_to_outline2 (verdictp :str ,outline2 ,depth_p :int =0 ):
            if depth_p >4 or not isinstance (outline2 ,dict ):
                return verdictp [:400 ]
            enum_p =outline2 .get ('enum')
            if isinstance (enum_p ,list )and enum_p :
                low_p =(verdictp or '').lower ()
                for opt_p in enum_p :
                    if isinstance (opt_p ,str )and re .search ('\\b'+re .escape (opt_p .lower ())+'\\b',low_p ):
                        return opt_p 
                return enum_p [0 ]
            kind =_outline2_variety (outline2 )
            if not kind :
                for key in ('anyOf','oneOf','allOf'):
                    branch_p =outline2 .get (key )
                    if isinstance (branch_p ,list )and branch_p :
                        for sub in branch_p :
                            if isinstance (sub ,dict )and sub .get ('type')!='null':
                                return _force2_to_outline2 (verdictp ,sub ,depth_p +1 )
                kind ='string'
            if kind =='array':
                items =outline2 .get ('items')or {}
                parts_p =[p_p .strip (' -*\t')for p_p in re .split ('[\\n;]|,(?![^(]*\\))',verdictp or '')]
                parts_p =[p_p [:400 ]for p_p in parts_p if p_p ][:20 ]
                if not parts_p :
                    parts_p =[verdictp [:400 ]]
                return [_force2_to_outline2 (p_p ,items ,depth_p +1 )for p_p in parts_p ]
            if kind =='object':
                props_p =outline2 .get ('properties')or {}
                required_p =outline2 .get ('required')or list (props_p .keys ())
                out_p ={}
                for key in required_p :
                    out_p [key ]=_force2_to_outline2 (verdictp ,props_p .get (key )or {},depth_p +1 )
                return out_p 
            if kind in ('number','integer'):
                found_p =_NUM_IN_TEXT_RE_P .search (_TAG_NUM_RE .sub (' ',verdictp or ''))
                if found_p is None :
                    return 0 
                val_p =found_p .group (0 ).replace (',','')
                try :
                    return int (val_p )if kind =='integer'else float (val_p )
                except Exception :
                    return 0 
            if kind =='boolean':
                return not re .match ('\\s*(no\\b|false\\b|none\\b)',verdictp or '',re .I )
            return (verdictp or '')[:400 ]
        _MONOLOGUE_OPENER_RE =re .compile ("^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|was|am|need|will|can)\\b|i(?:'ll|'ve|'m)\\b|let me\\b|let's\\b|first,? i\\b|having (?:now )?\\w+\\b|okay\\b|alright\\b|to answer this\\b|my research\\b)",re .IGNORECASE )
        _ABBREV_REMAINDER_RE =re .compile ('(?:\\b[A-Z]|\\b(?:Inc|Ltd|Co|No|vs|St|Dr|Mr|Ms|Mt|Jr|Sr|etc|e\\.g|i\\.e))\\.$')

        def _shear_opener_monologue (text :str )->str :
            t_p =(text or '').strip ()
            if not t_p :
                return t_p 
            for _ in range (2 ):
                parts_p =re .split ('(?<=[.!?])\\s+',t_p ,maxsplit =1 )
                if len (parts_p )!=2 :
                    break 
                head_p ,rest_p =(parts_p [0 ],parts_p [1 ].strip ())
                if _TAG_NUM_RE .search (head_p ):
                    break 
                if _MONOLOGUE_OPENER_RE .match (head_p )is None :
                    break 
                if len (head_p .split ())<4 or _ABBREV_REMAINDER_RE .search (head_p )is not None :
                    break 
                if len (rest_p )<120 or _TAG_NUM_RE .search (rest_p )is None :
                    break 
                t_p =rest_p 
            return t_p 

        def _lid (text :str )->str :
            t_p =(text or '').strip ()
            if len (t_p )>VERDICT_GLYPH_LID :
                return t_p [:VERDICT_GLYPH_LID -16 ]+' …'
            return t_p 
        _NUM_CMP_RE_P =re .compile ('([-+]?\\d[\\d,]*(?:\\.\\d+)?)\\s*(>=|<=|=>|=<|>|<)\\s*([-+]?\\d[\\d,]*(?:\\.\\d+)?)')
        _VERDICT_RE_P =re .compile ('(qualifies|does not qualify|excluded|fails|no\\b|yes\\b)',re .I )
        _PRIMARY_DOMAIN2_RE =re .compile ('\\.gov$|\\.gov\\.|\\.mil$|\\.edu$|europa\\.eu|\\.un\\.org|worldbank\\.org|imf\\.org|oecd\\.org|sec\\.gov|federalreserve\\.gov|census\\.gov|bls\\.gov|fec\\.gov|nasa\\.gov|who\\.int',re .I )
        _OFFICIAL_HINT_RE_P =re .compile ('investor|\\bir\\.|/investors?|annual-?report|press-?release|newsroom|/filing|10-k|20-f|official|statistics|factsheet|fact-?sheet',re .I )
        _AGGREGATOR_RE_P =re .compile ('pinterest|quora|reddit|facebook|twitter|x\\.com|tiktok|medium\\.com|blogspot|wordpress|answers\\.|ehow|wikihow|coursehero|scribd|slideshare|tripadvisor|amazon\\.',re .I )

        def _arithmetic_contradictions_p (verdictp :str )->list [str ]:
            problems_p :list [str ]=[]
            for line_p in (verdictp or '').split ('\n'):
                for chunk_p in re .split ('[;.]\\s+',line_p ):
                    match =_NUM_CMP_RE_P .search (chunk_p )
                    if match is None :
                        continue 
                    remain ,op_p ,right_p =(_as_index2 (match .group (1 )),match .group (2 ),_as_index2 (match .group (3 )))
                    if remain is None or right_p is None :
                        continue 
                    if op_p in ('>',):
                        holds_p =remain >right_p 
                    elif op_p in ('<',):
                        holds_p =remain <right_p 
                    elif op_p in ('>=','=>'):
                        holds_p =remain >=right_p 
                    else :
                        holds_p =remain <=right_p 
                    verdict_p =_VERDICT_RE_P .search (chunk_p )
                    if verdict_p is None :
                        if not holds_p :
                            problems_p .append ("'%s' is false: %s %s %s"%(chunk_p .strip ()[:90 ],match .group (1 ),op_p ,match .group (3 )))
                        continue 
                    said_yes_p =verdict_p .group (1 ).lower ()in ('qualifies','yes')
                    if said_yes_p !=holds_p :
                        problems_p .append ("'%s' -- %s %s %s is %s, so the verdict is inverted"%(chunk_p .strip ()[:90 ],match .group (1 ),op_p ,match .group (3 ),holds_p ))
            return problems_p [:6 ]

        def _coverage_voids (verdictp :str ,facts_p :list [dict ])->list [str ]:
            text =' '.join ((verdictp or '').split ()).lower ()
            if not text :
                return []
            missing_p :list [str ]=[]
            seen_p :set =set ()
            for slot in facts_p :
                label_p =(slot .get ('label')or '').strip ()
                if len (label_p )<3 or not slot .get ('value'):
                    continue 
                key =label_p .lower ()
                if key in seen_p :
                    continue 
                seen_p .add (key )
                if key not in text :
                    missing_p .append ('%s (established as %s [%s]) is never mentioned'%(label_p ,slot ['value'],slot .get ('n',0 )))
            return missing_p [:8 ]

        def _opener_disagrees_with_body (verdictp :str ,facts_p :list [dict ])->bool :
            text =verdictp or ''
            if not text .strip ():
                return False 
            parts_p =re .split ('(?<=[.!?])\\s+',' '.join (text .split ()))
            if len (parts_p )<2 :
                return False 
            openerp =parts_p [0 ].lower ()
            rest_p =' '.join (parts_p [1 :]).lower ()
            for slot in facts_p :
                label_p =(slot .get ('label')or '').strip ().lower ()
                if len (label_p )<3 or not slot .get ('value'):
                    continue 
                if label_p in openerp :
                    continue 
                for cue_p in ('complete list','therefore','qualifying jurisdictions are','the answer is','in summary','final list'):
                    idx_p =rest_p .find (cue_p )
                    if idx_p >=0 and label_p in rest_p [idx_p :idx_p +260 ]:
                        return True 
            return False 

        def _provenance_rank (url :str ,title :str ,annotation :str ,ask_p :str )->int :
            blob_p ='%s %s'%(url or '',title or '')
            rank_p =50 
            if _PRIMARY_DOMAIN2_RE .search (url or ''):
                rank_p =5 
            elif _OFFICIAL_HINT_RE_P .search (blob_p ):
                rank_p =15 
            elif 'wikipedia.org'in (url or '').lower ():
                rank_p =25 
            if _AGGREGATOR_RE_P .search (url or ''):
                rank_p =90 
            text =(annotation or '').lower ()
            lexemes =[w_p for w_p in re .findall ('[a-z]{4,}',(ask_p or '').lower ())][:12 ]
            hits_p =sum ((1 for w_p in set (lexemes )if w_p in text ))
            digits_p =len (re .findall ('\\d',text ))
            rank_p -=min (hits_p ,8 )*2 
            rank_p -=4 if digits_p >=12 else 0 
            return rank_p 

        def _as_index2 (crude :str ):
            try :
                return float (crude .replace (',','').lstrip ('+'))
            except Exception :
                return None 
        _MARKER_RE_P =re .compile ('\\[(\\d{1,3})\\]')

        async def query (query :Query )->Response :
            query2 =(query .text or '').strip ()
            if not query2 :
                return Response (text ='No question provided.')
            try :
                return await _resolve2 (query ,query2 )
            except Exception :
                return Response (text =f'Best-effort answer unavailable for: {query2[:500]}')
        INQUIRY2_BUFFER_S =53.0 
        SEAL_LIMIT2_S =46.0 
        SEAL_LOWER_RATION_S =20.0 

        def _tag_tally (text :str )->int :
            return len (set (_TAG_MARK_RE .findall (text or '')))

        async def _mandatory2_seal (query2 :str ,vault :SpecimenVault ,tableau :str ,cutoff :float )->str :
            ration =min (SEAL_LIMIT2_S ,cutoff -monotonic ()-BREVIARY_REMAINDER_S )
            if ration <SEAL_LOWER_RATION_S or not vault .rows :
                return ''
            specimen =tableau or _vault_breviary (vault )
            if not specimen :
                return ''
            system_p =ORBIT_STATUTE +'\n\nRESEARCH IS OVER. You have no tools and nothing further to gather. Write the final answer from the evidence board below, which holds every item collected, strongest source first. Cite its [n] exactly as written; never invent one. Cover every part of the question -- this is the answer that will be scored.'
            try :
                return (await _dialogue_bare (LLM_TRACK_A ,ORBIT_MODEL_A ,system_p ,'QUESTION: %s\n\n%s'%(query2 ,specimen [:60000 ]),max_tokens =2600 ,timeout =ration )).strip ()
            except Exception :
                return ''


                # ── candidate/constraint matrix ────────────────────────────────
        LATTICE_LIMIT2_S =28.0 
        LATTICE_LOWER_SLACK_S =105.0 
        UPPER_VOID_QUERIES =4 
        UPPER_VOID_PAGES =3 
        VOID_PLUG_LOWER_SLACK_S =72.0 

        def _tableau_breviary_for_lattice (vault :SpecimenVault ,query2 :str ,char_cap :int =58000 )->str :
            """Numbered evidence digest for the matrix pass (board-ranked)."""
            tableau =_paint_tableau (vault ,query2 ,char_cap =char_cap )
            if tableau :
                return tableau 
                # fallback: raw previews in ledger order
            parts_p =[]
            spent_p =0 
            for i_p ,slot in enumerate (vault .rows ,1 ):
                slab =f"[{i_p}] {(slot.get('title') or '')}\n{(slot.get('preview') or slot.get('text') or '')[:1200]}"
                if spent_p +len (slab )>char_cap :
                    break 
                parts_p .append (slab )
                spent_p +=len (slab )
            return "\n\n".join (parts_p )

        def _stock_lattice_blueprint (query2 :str )->dict :
            """Lightweight plan stub so the matrix has conditions to work against."""
            ensemble_q =_needs_ensemble_fullness (query2 )
            super_q_p =_needs_apex_proof (query2 )
            constraints =[]
            if ensemble_q :
                constraints =["belongs to the named class","satisfies every stated filter"]
            elif super_q_p :
                constraints =["belongs to the named class","has a comparable deciding value"]
            else :
                constraints =["answers the asked question"]
            return {"conditions":constraints ,"pages":[],"queries":[],"answer_kind":"set"if ensemble_q else "entity"}

        async def _nominee_lattice (query2 :str ,blueprint :dict ,vault :SpecimenVault ,
        cutoff :float ,previous :dict |None =None )->dict :
            breviary =_tableau_breviary_for_lattice (vault ,query2 )
            if not breviary or (cutoff -monotonic ())<LATTICE_LOWER_SLACK_S :
                return {}
            prior_p =json .dumps (previous or {},ensure_ascii =False )[:18000 ]
            prompt_p =(
            "Construct an evidence-controlled nominee lattice. Return JSON only with keys: answer_hypothesis (concise), candidates (array of objects with name, passed_conditions, failed_conditions, unknown_conditions, evidence_numbers), unresolved (array), queries (0-6 targeted searches), pages (0-6 objects with url and focus). For a set/intersection question, place a nominee in answer_hypothesis ONLY when direct evidence shows every condition. Preserve Boolean OR in the plan: satisfying any member of an OR passes that condition. When a previous lattice is supplied, update it in place without dropping prior nominees. Never invent an evidence number."
            "answer_hypothesis (concise), candidates (array of objects with name, "
            "passed_conditions, failed_conditions, unknown_conditions, evidence_numbers), "
            "unresolved (array), queries (0-6 targeted searches), pages (0-6 objects with "
            "url and focus). For a set/intersection question, include a candidate in "
            "answer_hypothesis ONLY when direct evidence shows every condition. Preserve "
            "Boolean OR in the plan: satisfying any member of an OR passes that condition. "
            "When a previous matrix is supplied, update it in place without dropping prior "
            "candidates. Never invent an evidence number.\n\n"
            f"QUESTION:\n{query2}\n\nPLAN:\n{json.dumps(blueprint, ensure_ascii=False)[:9000]}\n\n"
            f"PREVIOUS MATRIX:\n{prior_p}\n\nNUMBERED EVIDENCE:\n{breviary}"
            )
            try :
                crude =await _dialogue_bare (
                LLM_TRACK_A ,INSPECT_MODEL ,
                "You are a strict adjudicator. Separate attested victors from merely plausible extras. JSON only.",
                prompt_p ,
                max_tokens =4300 ,
                timeout =max (8.0 ,min (LATTICE_LIMIT2_S ,cutoff -monotonic ()-62.0 )),
                think ={"enabled":True ,"effort":"low"},
                )
                crude =re .sub (r"^```(?:json)?\s*|\s*```$","",crude .strip (),flags =re .I |re .M )
                report_p =json .loads (crude )
                return report_p if isinstance (report_p ,dict )else {}
            except Exception :
                return {}

        def _lattice_void_queries (lattice :dict )->list [str ]:
            out_p :list [str ]=[]
            for value_p in lattice .get ("queries",[])or []:
                if isinstance (value_p ,str ):
                    q_p =" ".join (value_p .split ())[:500 ]
                    if q_p and q_p not in out_p :
                        out_p .append (q_p )
            for value_p in lattice .get ("unresolved",[])or []:
                q_p =" ".join (str (value_p ).split ())[:500 ]
                if q_p and q_p not in out_p :
                    out_p .append (q_p )
            for nominee in lattice .get ("candidates",[])or []:
                if not isinstance (nominee ,dict ):
                    continue 
                name_p =" ".join (str (nominee .get ("name")or "").split ())
                for value_p in nominee .get ("unknown_conditions",[])or []:
                    q_p =" ".join (f'"{name_p}" {value_p}'.split ())[:500 ]
                    if name_p and q_p not in out_p :
                        out_p .append (q_p )
            return out_p [:UPPER_VOID_QUERIES ]

        def _attested_nominees (lattice :dict ,blueprint :dict )->list [str ]:
            required_p =max (1 ,len (blueprint .get ("conditions",[])or []))
            victors :list [str ]=[]
            for nominee in lattice .get ("candidates",[])or []:
                if not isinstance (nominee ,dict ):
                    continue 
                name_p =str (nominee .get ("name")or "").strip ()
                passed_p =nominee .get ("passed_conditions")or []
                failed_p =nominee .get ("failed_conditions")or []
                unknown_p =nominee .get ("unknown_conditions")or []
                if name_p and not failed_p and not unknown_p and len (passed_p )>=required_p :
                    victors .append (name_p )
            return victors [:20 ]

        def _lattice_nominee_names (lattice :dict )->set [str ]:
            return {
            str (c_p .get ("name")or "").strip ().casefold ()
            for c_p in (lattice .get ("candidates")or [])
            if isinstance (c_p ,dict )and str (c_p .get ("name")or "").strip ()
            }

        def _lattice_stride (lattice :dict ,blueprint :dict )->tuple :
            attested =len (_attested_nominees (lattice ,blueprint ))
            resolved_c_p =resolved_cond_p =unknown_p =0 
            for c_p in lattice .get ("candidates",[])or []:
                if not isinstance (c_p ,dict ):
                    continue 
                unk_p =c_p .get ("unknown_conditions")or []
                if not unk_p :
                    resolved_c_p +=1 
                resolved_cond_p +=len (c_p .get ("passed_conditions")or [])+len (c_p .get ("failed_conditions")or [])
                unknown_p +=len (unk_p )
            return (attested ,resolved_c_p ,resolved_cond_p ,-unknown_p )

        def _cautious_lattice_renew (previous :dict ,refreshed_p :dict ,blueprint :dict )->bool :
            if not refreshed_p :
                return False 
            old_names_p =_lattice_nominee_names (previous )
            new_names_p =_lattice_nominee_names (refreshed_p )
            if old_names_p and not old_names_p .issubset (new_names_p ):
                return False 
            old_w_p ={n_p .casefold ()for n_p in _attested_nominees (previous ,blueprint )}
            new_w_p ={n_p .casefold ()for n_p in _attested_nominees (refreshed_p ,blueprint )}
            if old_w_p and not old_w_p .issubset (new_w_p ):
                return False 
            return (len (new_names_p )>len (old_names_p )
            or _lattice_stride (refreshed_p ,blueprint )>_lattice_stride (previous ,blueprint ))

        def _proposition_backing_defects (verdictp :str ,vault :SpecimenVault )->list [str ]:
            """every cited numeric claim should appear in a cited row's text."""
            defects :list [str ]=[]
            if not verdictp or not vault .rows :
                return defects 
                # find [n] citations near numbers
            for m_p in re .finditer (r"(\d[\d,]*(?:\.\d+)?)[^\n]{0,40}?\[(\d{1,3})\]",verdictp ):
                value_p ,n_s_p =m_p .group (1 ),m_p .group (2 )
                try :
                    n_p =int (n_s_p )
                except ValueError :
                    continue 
                if not (1 <=n_p <=len (vault .rows )):
                    defects .append (f"cited [{n_p}] does not exist for value {value_p}")
                    continue 
                body_p =(vault .rows [n_p -1 ].get ("text")
                or vault .rows [n_p -1 ].get ("preview")or "")
                compact_body_p =body_p .replace (",","").replace (" ","")
                compact_val_p =value_p .replace (",","")
                if compact_val_p and compact_val_p not in compact_body_p and value_p not in body_p :
                    defects .append (f"value {value_p} cited [{n_p}] is not visible in that source text")
            return defects [:8 ]

        async def _lattice_void_plug (query2 :str ,lattice :dict ,vault :SpecimenVault ,
        cutoff :float )->int :
            """One parallel burst of matrix-driven searches. Returns how many queries ran."""
            if (cutoff -monotonic ())<VOID_PLUG_LOWER_SLACK_S :
                return 0 
            queries_p =_lattice_void_queries (lattice )
            if not queries_p :
                return 0 
            ration =max (6.0 ,min (SCOUT_LIMIT2_S *2 +8.0 ,
            cutoff -monotonic ()-LOWER_REMAINDER_S -INQUIRY2_BUFFER_S *0.3 ))
            tasks_p =[asyncio .ensure_future (_do_scout (qy_p ,vault ))for qy_p in queries_p ]
            try :
                await asyncio .wait (tasks_p ,timeout =ration )
            except Exception :
                pass 
            filled_p =0 
            for t_p in tasks_p :
                if t_p .done ():
                    try :
                        _seal_implement_emission (t_p .result (),vault )
                        filled_p +=1 
                    except Exception :
                        pass 
                else :
                    t_p .cancel ()
            return filled_p 

        async def _lattice_valved_lane2 (query2 :str ,vault :SpecimenVault ,
        cutoff :float )->tuple [str ,list [str ]]:
            """Creative: one matrix pass + optional gap fill before forced commit.

            Returns (matrix_block_for_commit, verified_winner_names).
            """
            if not (_needs_ensemble_fullness (query2 )or _needs_apex_proof (query2 )):
                return "",[]
            if (cutoff -monotonic ())<LATTICE_LOWER_SLACK_S :
                return "",[]
            if not vault .rows :
                return "",[]
            blueprint =_stock_lattice_blueprint (query2 )
            lattice =await _nominee_lattice (query2 ,blueprint ,vault ,cutoff )
            if not lattice :
                return "",[]
                # one gap-fill if unresolved remain
            if (lattice .get ("unresolved")or _lattice_void_queries (lattice ))and (cutoff -monotonic ())>VOID_PLUG_LOWER_SLACK_S :
                await _lattice_void_plug (query2 ,lattice ,vault ,cutoff )
                refreshed_p =await _nominee_lattice (query2 ,blueprint ,vault ,cutoff ,previous =lattice )
                if _cautious_lattice_renew (lattice ,refreshed_p ,blueprint ):
                    lattice =refreshed_p 
            victors =_attested_nominees (lattice ,blueprint )
            # render compact board for the commit prompt
            lines_p =["NOMINEE LATTICE (evidence-controlled — attested victors are the floor; do not drop them):"]
            for c_p in (lattice .get ("candidates")or [])[:24 ]:
                if not isinstance (c_p ,dict ):
                    continue 
                name_p =str (c_p .get ("name")or "").strip ()
                if not name_p :
                    continue 
                passed_p =c_p .get ("passed_conditions")or []
                failed_p =c_p .get ("failed_conditions")or []
                unknown_p =c_p .get ("unknown_conditions")or []
                cites_p =",".join (str (x_p )for x_p in (c_p .get ("evidence_numbers")or [])[:4 ])
                status_p ="VERIFIED"if name_p in victors else (
                "EXCLUDED"if failed_p else ("OPEN"if unknown_p else "PARTIAL"))
                lines_p .append (f"  [{status_p}] {name_p} — passed={len(passed_p)} failed={len(failed_p)} unknown={len(unknown_p)} cites=[{cites_p}]")
            if victors :
                lines_p .append ("ATTESTED VICTORS (must appear in the answer unless later evidence overturns them): "
                +"; ".join (victors ))
            return "\n".join (lines_p ),victors 


        async def _inquiry2_then_seal (query2 :str ,dossier :str ,vault :SpecimenVault ,cutoff :float )->tuple [str ,list [dict ]]:
            inquiry2_cutoff =cutoff -INQUIRY2_BUFFER_S 
            pending_p ,messages =('',[])
            try :
                pending_p ,messages =await _orbit (query2 ,dossier ,vault ,inquiry2_cutoff ,UPPER_TICKS )
            except Exception :
                pending_p ,messages =('',[])
            # named-origin recovery before lattice / seal
            try:
                _filled = await _origin_recovery_h(query2, vault, cutoff)
                if _filled:
                    _onames = _named_origins_h(query2)
                    messages = list(messages) + [{
                        'role': 'system',
                        'content': (
                            'ORIGIN RECOVERY — fresh hunts ran for the ask-named origin(s): '
                            + ', '.join(_onames)
                            + '. Prefer these packets over aggregators when sealing.'
                        ),
                    }]
            except Exception:
                pass
                # creative: matrix-gated pass for set/superlative before the reserved commit
            lattice_slab ,victors =('',[])
            try :
                lattice_slab ,victors =await _lattice_valved_lane2 (query2 ,vault ,cutoff )
            except Exception :
                lattice_slab ,victors =('',[])
            if lattice_slab :
                messages =list (messages )+[{'role':'system','content':lattice_slab }]
            tableau =_paint_tableau (vault ,query2 )
            if lattice_slab :
                tableau =lattice_slab +'\n\n'+tableau 
            committed_p =await _mandatory2_seal (query2 ,vault ,tableau ,cutoff )
            # refuse a commit that drops every matrix-verified winner
            if victors and _is_viable_verdict (committed_p ):
                kept_p =sum (1 for w_p in victors if w_p .casefold ()in committed_p .casefold ())
                if kept_p ==0 and _is_viable_verdict (pending_p ):
                    committed_p =pending_p 
            if _is_viable_verdict (pending_p ):
            # still prefer a pending answer that already lists the winners
                if victors :
                    p_kept_p =sum (1 for w_p in victors if w_p .casefold ()in pending_p .casefold ())
                    c_kept_p =sum (1 for w_p in victors if w_p .casefold ()in (committed_p or '').casefold ())if _is_viable_verdict (committed_p )else -1 
                    if p_kept_p >=c_kept_p :
                        return (pending_p ,messages )
                else :
                    return (pending_p ,messages )
            if _is_viable_verdict (committed_p ):
                return (committed_p ,messages )
            return (pending_p ,messages )

        async def _resolve2 (query :Query ,query2 :str )->Response :
            cutoff =monotonic ()+WALL_RATION_S 
            try :
                info_p =await tooling_info (timeout =10.0 )
                _burn_annotation (info_p )
            except Exception :
                pass 
            rough =''
            dossier =''
            try :
                if _burn_remain ()>=DOSSIER_LOWER_USD and cutoff -monotonic ()>120.0 :
                    rough ,dossier =await _knowledge_dossier (query2 )
            except Exception :
                dossier =''
            vault =SpecimenVault ()
            verdictp =''
            messages :list [dict ]=[]
            try :
                verdictp ,messages =await _inquiry2_then_seal (query2 ,dossier ,vault ,cutoff )
            except Exception :
                verdictp =''
            try :
                if _is_viable_verdict (verdictp )and cutoff -monotonic ()>75.0 and (_burn_remain ()>=INSPECT_LOWER_USD ):
                    patched_p =await _inspect_splice (query2 ,verdictp ,messages ,vault ,cutoff )
                    if _is_viable_verdict (patched_p ):
                        verdictp =patched_p 
            except Exception :
                pass 
                # citation-slice support check — surface invisible values
            try :
                backing =_proposition_backing_defects (verdictp ,vault )if _is_viable_verdict (verdictp )else []
                if backing and cutoff -monotonic ()>70.0 and (_burn_remain ()>=INSPECT_LOWER_USD ):
                    messages =list (messages )+[{'role':'system','content':
                    'FOOTNOTE BACKING GAPS — these values are tagged but not visible in the '
                    'cited source text:\n- '+'\n- '.join (backing )+
                    '\nRewrite so every cited figure appears inside its [n] source, or '
                    're-cite a source that actually contains it.'}]
                    fixed_p ,messages =await _orbit (query2 ,'',vault ,cutoff ,
                    INSPECT_SURPLUS_TICKS +1 ,carry =messages ,
                    allow_tools_in_wrapup =True )
                    if _is_viable_verdict (fixed_p )and len (fixed_p )>=int (len (verdictp )*0.6 ):
                        verdictp =fixed_p 
            except Exception :
                pass 
            try :
                if _is_viable_verdict (verdictp )and cutoff -monotonic ()>INSPECT_LOWER_SLACK_S :
                    _slots =[{'label':(r_p .get ('title')or '')[:80 ],'value':'','n':i_p +1 ,'verified':True }for i_p ,r_p in enumerate (vault .rows )]
                    _defects_p =_arithmetic_contradictions_p (verdictp )
                    if _opener_disagrees_with_body (verdictp ,_slots ):
                        _defects_p .append ('the opening list omits a member the answer later endorses; sentence one must already carry the final, complete list')
                    if _defects_p :
                        _inspect_cutoff =min (cutoff ,monotonic ()+INSPECT_REWORK_UPPER_S )
                        _fixed_p =await _orbit (query2 ,dossier ,vault ,_inspect_cutoff ,1 ,carry =list (messages )+[{'role':'system','content':'Your answer has these defects:\n- '+'\n- '.join (_defects_p [:6 ])+'\nRecompute every comparison and rewrite the COMPLETE answer from scratch. Do not append a correction: sentence one must already state the final, complete answer.'}])
                        _cand_p =_fixed_p [0 ]if isinstance (_fixed_p ,tuple )else ''
                        if _is_viable_verdict (_cand_p )and (not _arithmetic_contradictions_p (_cand_p )):
                            verdictp =_cand_p 
            except Exception :
                pass 
            if not _is_viable_verdict (verdictp )and vault .rows :
                try :
                    rescued_p =await _inscribe_from_breviary (query2 ,vault ,cutoff )
                    if _is_viable_verdict (rescued_p ):
                        verdictp =rescued_p 
                except Exception :
                    pass 
            if not _is_viable_verdict (verdictp )and vault .rows :
                det_p =_mechanical_verdict (query2 ,vault )
                if _is_viable_verdict (det_p ):
                    verdictp =det_p 
            if not _is_viable_verdict (verdictp ):
                safety =_sterilize_rough (rough )or await _knowledge_fallback2 (query2 ,cutoff )
                if _is_viable_verdict (safety ):
                    verdictp =safety 
            try :
                citations =_footnotes_for (verdictp ,vault )
            except Exception :
                citations =[]
            verdictp =_canonize_braces (verdictp )
            verdictp =_shear_opener_monologue (verdictp )
            verdictp =_verdict_line_only (verdictp ,query2 )
            text =_lid (verdictp )or f'Best-effort answer unavailable for: {query2[:400]}'
            if query .output_schema is not None :
                structured_p =None 
                try :
                    structured_p =await _outline2_emission (query2 ,verdictp ,query .output_schema ,cutoff )
                except Exception :
                    structured_p =None 
                if structured_p is not None :
                    try :
                        structured_p =_verbatim_structured_p (structured_p ,vault )
                    except Exception :
                        pass 
                    try :
                        return Response (output =structured_p ,citations =citations or None )
                    except Exception :
                        structured_p =None 
                basis_p =verdictp if _is_viable_verdict (verdictp )else ''
                if not basis_p :
                    basis_p =_mechanical_verdict (query2 ,vault )
                if not basis_p or _STUB2_VERDICT_RE .match (basis_p .strip ()):
                    basis_p =query2 [:400 ]
                try :
                    mandatory2 =_force2_to_outline2 (_lid (basis_p ),query .output_schema )
                    return Response (output =mandatory2 ,citations =citations or None )
                except Exception :
                    try :
                        return Response (output =_lid (basis_p )[:2000 ],citations =citations or None )
                    except Exception :
                        pass 
            try :
                return Response (text =text ,citations =citations or None )
            except Exception :
                return Response (text =text )
        return query 


class LightCorridor :

    def _compile (self ):
        import asyncio 
        import json 
        import re 
        from collections .abc import Mapping 
        from dataclasses import dataclass ,field 
        from time import monotonic 
        from harnyx_miner_sdk .api import fetch_page ,llm_chat ,search_web 
        from harnyx_miner_sdk .decorators import entrypoint 
        from harnyx_miner_sdk .query import CitationRef ,CitationSlice ,Query ,Response 
        VERSION_P ='q5-r1-easy-sliceproof-20260805-sliceproof-doctrine'
        LLM_PROVIDER_P ='chutes'
        MODEL_ORBIT ='zai-org/GLM-5-TEE'
        MODEL_SAFETY ='deepseek-ai/DeepSeek-V3.2-TEE'
        MODEL_INSPECT ='Qwen/Qwen3.6-27B-TEE'
        ORBIT_TRIES_PRIMARY =2 
        SCOUT_PROVIDER ='parallel'
        _REASONING_REQUIRED_P =('Qwen/Qwen3.6',)

        def _deliberate_for (model :str ,*,want :bool )->dict :
            if any ((model .startswith (p_p )for p_p in _REASONING_REQUIRED_P )):
                return {'enabled':True ,'effort':'low'}
            return {'enabled':True ,'effort':'low'}if want else {'enabled':False }

        def _ladder_p (primary_p :str )->list [tuple [str ,int ]]:
            rungs_p =[(primary_p ,ORBIT_TRIES_PRIMARY )]
            if MODEL_SAFETY !=primary_p :
                rungs_p .append ((MODEL_SAFETY ,1 ))
            return rungs_p 
        WALL_RATION_S =260.0 
        DOSSIER_LIMIT2_S =45.0 
        INSPECT_LIMIT2_S =30.0 
        SEAL_LIMIT2_S =55.0 
        PULL_LIMIT2_S =16.0 
        UPPER_INVOKES_PER_TICK =8 
        TICK_LIMIT2_S =70.0 
        SEAL_BUFFER_S =46.0 
        LOWER_REMAINDER_S =8.0 
        UPPER_TICKS =14 
        SCOUT_LIMIT2_S =18.0 
        UPPER_REPAIRS =2 
        SCOUT_OUTCOMES =8 
        SCOUT_PASSAGE_GLYPHS =520 
        FOLIO2_HEAD_GLYPHS =2600 
        FOLIO2_PANE_GLYPHS =3400 
        FOLIO2_PANES =3 
        SPECIMEN_GLYPH_RATION =104000 
        FOOTNOTE_LID =26 
        VERDICT_GLYPH_LID =48000 
        UPPER_SOW_QUERIES =3 
        FOLIO2_GLIMPSE_GLYPHS =12000 
        _ENSEMBLE_ASK_RE =re .compile ('\\b(?:list|name|identify|enumerate|which)\\b[^?]{0,60}\\b(?:all|every|each|both)\\b',re .I )
        _ENSEMBLE_JOIN_RE =re .compile ('\\b(?:both|as well as|and also|and had|and received)\\b',re .I )
        _PLURAL2_ASK_RE =re .compile ('\\b(?:which|what)\\b(?:\\s+\\w+){0,2}?\\s+([a-z]{3,}s)\\b',re .I )
        _PLURAL2_NOT =frozenset ('was is has does its this thus across process business series species status analysis basis focus versus previous various famous others always perhaps'.split ())
        _TOP_RE_P =re .compile ('\\b(?:highest|lowest|largest|smallest|greatest|fewest|longest|shortest|oldest|newest|youngest|maximum|minimum)\\b|(?<!at )\\b(?:most|least)\\b',re .I )
        _ENUM_LIST_RE_P =re .compile ('\\bwhich of the (?:following|these)\\b|\\bfrom the following list\\b',re .I )
        _OR_LIST_RE_P =re .compile ('[:,]\\s*[^,:?]{2,60}(?:,\\s*[^,:?]{2,60}){1,}\\s*,?\\s+or\\s+',re .I )
        _CONSTRAINT_RE_P =re .compile ('\\b(?:at least|at most|no more than|no fewer than|greater than|less than|fewer than|more than|over|under|above|below|exceed(?:s|ing)?|between\\s+[^,]{1,30}\\s+and)\\b',re .I )
        _EST_RE_P =re .compile ('\\b([a-z]{3,})est\\b')
        _EST_NOT_P =frozenset ('conquest tempest incest behest zest quest crest chest guest jest pest vest midwest southwest northwest bequest imprest inquest gest wrest'.split ()+'interest honest modest protest request suggest forest harvest invest'.split ()+'arrest contest digest manifest earnest rest best west nest test'.split ())
        _NAMED_PROVENANCE_RE =re .compile ("\\b(?:according to|per|from|listed (?:in|on)|in the)\\s+((?:the\\s+)?[A-Z][\\w.'&-]*(?:\\s+[A-Z][\\w.'&-]*){0,4})",re .S )
        _PROVENANCE_WORD_RE =re .compile ('\\b(wikipedia|wikidata|imdb|britannica|eurovisionworld|usgs|nasa|noaa|baseball-reference|basketball-reference|box office mojo|rotten tomatoes|metacritic|billboard|discogs|goodreads|transfermarkt|olympedia|pubmed|arxiv|sec|edgar|eurostat|world bank|imf|census|worldometer|worldometers|the numbers|thenumbers|citypopulation|macrotrends|statista|boxofficemojo)\\b',re .I )
        _PROVENANCE_NOUN_RE =re .compile ('\\b(?:wiki\\w*|article|page|site|database|dataset|data|table|list|index|factsheet|fact sheet|report|filing|registry|catalog(?:ue)?|almanac|encyclopedia|archive|records?|statistics|census|survey|bulletin|\\.(?:com|org|net|gov|edu))\\b',re .I )

        def _has_top_p (text :str )->bool :
            if _TOP_RE_P .search (text or ''):
                return True 
            return any ((m_p .group (0 ).lower ()not in _EST_NOT_P for m_p in _EST_RE_P .finditer (text or '')))

        def _wants_ensemble (query2 :str )->bool :
            q_p =' '.join ((query2 or '').split ())
            if not q_p :
                return False 
            if _ENSEMBLE_ASK_RE .search (q_p ):
                return True 
            if _ENUM_LIST_RE_P .search (q_p )or (re .search ('\\bwhich\\b',q_p ,re .I )and _OR_LIST_RE_P .search (q_p )):
                return True 
            head_p =_PLURAL2_ASK_RE .search (q_p )
            if head_p and head_p .group (1 ).lower ()not in _PLURAL2_NOT :
                if not _has_top_p (q_p )or re .search ('\\b(?:all|every|each)\\b',q_p ,re .I ):
                    return True 
            return bool (re .search ('\\bwhich\\b',q_p ,re .I ))and bool (_ENSEMBLE_JOIN_RE .search (q_p ))

        def _wants_tally_p (query2 :str )->bool :
            q_p =' '.join ((query2 or '').split ())
            if not q_p :
                return False 
            if _has_top_p (q_p )or re .search ('\\b(?:how many|how much|(?:most|least) (?:common|frequent))\\b',q_p ,re .I ):
                return True 
            return bool (re .search ('\\b(?:which|what)\\b',q_p ,re .I ))and len (_CONSTRAINT_RE_P .findall (q_p ))>=2 

        def _named_provenances (query2 :str )->list [str ]:
            found_p :list [str ]=[]
            for m_p in _PROVENANCE_WORD_RE .finditer (query2 or ''):
                name_p =m_p .group (1 ).strip ()
                if name_p .lower ()not in {f_p .lower ()for f_p in found_p }:
                    found_p .append (name_p )
            for m_p in _NAMED_PROVENANCE_RE .finditer (query2 or ''):
                name_p =re .sub ('^the\\s+','',m_p .group (1 ).strip (),flags =re .I ).strip (" .,'")
                if not _PROVENANCE_NOUN_RE .search (name_p ):
                    continue 
                if 2 <len (name_p )<60 and name_p .lower ()not in {f_p .lower ()for f_p in found_p }:
                    found_p .append (name_p )
            return found_p [:4 ]
        ORBIT_STATUTE ='You are a precise fact-finding agent. A pairwise judge scores you against a strong reference and only awards credit for claims whose citation points at a tool result that literally contains the supporting text. Ties go to the reference — so bare correctness is not enough; you must show more validated detail.\n\nINSTRUMENTS. web_search(query) yields numbered hits with short excerpts. read_page(url, focus) returns the page head plus the zones densest in your focus terms. Treat a search excerpt as a pointer: open the page before you stake a figure on it.\n\nFOOTNOTES. Every tool result has an index. Attach [n] at the claim site, not as a paragraph footer. One trailing [n] on a long paragraph supports only one claim. Never fabricate an index.\n\nFIGURES. Copy numbers exactly as printed — units, precision, notation. If you derive a value, show the cited inputs and label the derivation.\n\nEMPTY STRUCTURED OUTPUTS SCORE ZERO — never return [] when evidence exists. DUAL RANKINGS take the INTERSECTION. TABLE NAMES copy exactly as printed. LEAD. Sentence one is the direct answer in the shape the question requests. Proof follows. Skip process narration, skip hedging of verified facts, and never contradict a source you just cited.\n\nWhen the proof is in hand, write the final answer as plain prose — no announcement that you are about to answer.'
        ENSEMBLE_STATUTE2 ="SET ANSWER — this asks for a set; omitting one qualifying member scores like being wrong.\n1. Recover the full class the question ranges over (not a shortlist of survivors).\n2. Apply every stated filter; keep a member only when every filter is evidenced.\n3. Open with the complete set, then one line per member with its proving [n].\n4. Rejects get their own line naming the failed filter and its [n].\n5. Unsettled filters → keep the member and cite the strongest verified fact."
        TALLY_STATUTE2 ="SUPERLATIVE / COUNT — the answer is one item, but you cannot know which without the whole basin. Show the table.\n1. Enumerate the class.\n2. Pull the deciding metric for every member with citations.\n3. Compare; name the winner in sentence one.\n4. Keep the comparison table in the proof — a lone winner with no table is under-supported."

        def _provenance_statute2 (names_p :list [str ])->str :
            listed_p =', '.join (names_p )
            return f"NAMED SOURCE — this question specifies where the answer must come from: {listed_p}. Read THAT source and cite it. An aggregator or mirror carrying the same figures does not satisfy the constraint: a judge has scored us 0 on all four runs of a question whose data and conclusion it agreed were correct, purely because we answered from a different site than the one named. Search the named source directly (try 'site:' or its name in the query), read_page it, and quote its own wording. Only if it genuinely cannot be retrieved may you fall back — and then say so explicitly."

        def _contour_statute (query2 :str )->list [str ]:
            statute :list [str ]=[]
            if _wants_ensemble (query2 ):
                statute .append (ENSEMBLE_STATUTE2 )
            if _wants_tally_p (query2 ):
                statute .append (TALLY_STATUTE2 )
            named_p =_named_provenances (query2 )
            if named_p :
                statute .append (_provenance_statute2 (named_p ))
            return statute 

        @dataclass (slots =True )
        class Row :
            receipt_id :str 
            result_id :str 
            note_len :int 
            spans :tuple [tuple [int ,int ],...]
            kind :str 
            url :str =''
            title :str =''
            preview :str =''

        @dataclass (slots =True )
        class Ledger :
            rows :list [Row ]=field (default_factory =list )
            _seen :dict [tuple [str ,str ],int ]=field (default_factory =dict )

            def add (self ,slot :Row )->int :
                key =(slot .receipt_id ,slot .result_id )
                existing_p =self ._seen .get (key )
                if existing_p is not None :
                    prior_p =self .rows [existing_p -1 ]
                    merged_p =_merge_reaches (prior_p .spans +slot .spans )
                    self .rows [existing_p -1 ]=Row (receipt_id =prior_p .receipt_id ,result_id =prior_p .result_id ,note_len =max (prior_p .note_len ,slot .note_len ),spans =merged_p ,kind =prior_p .kind ,url =prior_p .url or slot .url ,title =prior_p .title or slot .title ,preview =max ((prior_p .preview ,slot .preview ),key =len ))
                    return existing_p 
                self .rows .append (slot )
                n_p =len (self .rows )
                self ._seen [key ]=n_p 
                return n_p 

            def cost (self ,n_p :int )->int :
                slot =self .rows [n_p -1 ]
                if not slot .spans :
                    return slot .note_len 
                return sum ((max (0 ,e_p -s_p )for s_p ,e_p in slot .spans ))

            def ref (self ,n_p :int )->CitationRef |None :
                if not 1 <=n_p <=len (self .rows ):
                    return None 
                slot =self .rows [n_p -1 ]
                if not slot .receipt_id or not slot .result_id :
                    return None 
                slices =[CitationSlice (start =s_p ,end =e_p )for s_p ,e_p in slot .spans if e_p >s_p ]
                if slices :
                    return CitationRef (receipt_id =slot .receipt_id ,result_id =slot .result_id ,slices =slices )
                return CitationRef (receipt_id =slot .receipt_id ,result_id =slot .result_id )

        def _merge_reaches (spans :tuple [tuple [int ,int ],...])->tuple [tuple [int ,int ],...]:
            ordered_p =sorted (((s_p ,e_p )for s_p ,e_p in spans if e_p >s_p ))
            if not ordered_p :
                return ()
            out_p =[list (ordered_p [0 ])]
            for s_p ,e_p in ordered_p [1 :]:
                if s_p <=out_p [-1 ][1 ]:
                    out_p [-1 ][1 ]=max (out_p [-1 ][1 ],e_p )
                else :
                    out_p .append ([s_p ,e_p ])
            return tuple (((s_p ,e_p )for s_p ,e_p in out_p ))
        _LEXEME_RE =re .compile ("[a-z0-9][a-z0-9'.\\-]{2,}")
        _LEXEME_STOP =frozenset ('the and for with from that this have has was were are is been its their there which what when where who whom whose how why all any both each more most other some such than then they them these those into over under about after before between during without within according listed page article table'.split ())

        def _lexemes (text :str )->set [str ]:
            return {w_p for w_p in _LEXEME_RE .findall ((text or '').casefold ())if w_p not in _LEXEME_STOP }

        def _dense_panes (annotation :str ,lexemes :set [str ],width_p :int ,k :int )->list [tuple [int ,int ]]:
            n_p =len (annotation )
            if n_p <=width_p or not lexemes :
                return [(0 ,min (n_p ,width_p ))]if n_p else []
            stride_p =max (400 ,width_p //4 )
            low_p =annotation .lower ()
            scored_p :list [tuple [int ,int ]]=[]
            pos_p =0 
            while True :
                seg_p =low_p [pos_p :pos_p +width_p ]
                scored_p .append ((sum ((1 for t_p in lexemes if t_p in seg_p )),pos_p ))
                if pos_p +width_p >=n_p :
                    break 
                pos_p +=stride_p 
            scored_p .sort (key =lambda hp :(-hp [0 ],hp [1 ]))
            picked_p :list [tuple [int ,int ]]=[]
            for hits_p ,start in scored_p :
                if len (picked_p )>=max (1 ,k ):
                    break 
                if picked_p and hits_p <=0 :
                    break 
                end =min (n_p ,start +width_p )
                if any ((start <pe_p and ps_p <end for ps_p ,pe_p in picked_p )):
                    continue 
                picked_p .append ((start ,end ))
            picked_p .sort ()
            return picked_p or [(0 ,min (n_p ,width_p ))]
        IMPLEMENT_SPECS =[{'type':'function','function':{'name':'web_search','description':'Web search. Returns numbered results with title, url and an excerpt.','parameters':{'type':'object','properties':{'query':{'type':'string','description':'the search query'}},'required':['query']}}},{'type':'function','function':{'name':'read_page','description':'Read a page. Returns its head plus the regions densest in your focus terms. Always read the page before relying on a figure.','parameters':{'type':'object','properties':{'url':{'type':'string','description':'the page url'},'focus':{'type':'string','description':'what you are looking for on the page'}},'required':['url']}}}]
        _SLOT_P ='\x00{}\x00'

        @dataclass (slots =True )
        class ToolOut :
            text :str 
            rows :list [Row ]=field (default_factory =list )

        def _seal (out_p :object ,vault :Ledger )->str :
            if isinstance (out_p ,str ):
                return out_p 
            if not isinstance (out_p ,ToolOut ):
                return f'# tool error: {out_p}'
            text =out_p .text 
            for i_p ,slot in enumerate (out_p .rows ):
                text =text .replace (_SLOT_P .format (i_p ),str (vault .add (slot )))
            return text 
        _SITE2_OP_RE =re .compile ('(?:\\b|^)site\\s*:\\s*\\S+\\s*',re .I )

        def _loosen_p (query :str )->str :
            out_p =_SITE2_OP_RE .sub ('',query or '').replace ('"',' ')
            return ' '.join (out_p .split ())

        async def _implement_scout (query :str ,cutoff :float )->ToolOut :
            query =' '.join ((query or '').split ())[:400 ]
            if not query :
                return ToolOut ('# web_search: empty query')
            attempts_p =[query ]
            loose_p =_loosen_p (query )
            if loose_p and loose_p !=query :
                attempts_p .append (loose_p )
            outcomes =()
            receipt_p =''
            for attempt_p in attempts_p :
                if cutoff -monotonic ()<LOWER_REMAINDER_S :
                    break 
                try :
                    bundle =await search_web ([attempt_p ],provider =SCOUT_PROVIDER ,num =SCOUT_OUTCOMES ,timeout =SCOUT_LIMIT2_S )
                except Exception :
                    continue 
                outcomes =tuple (getattr (bundle ,'results',())or ())
                receipt_p =getattr (bundle ,'receipt_id','')or ''
                if outcomes :
                    break 
            if not outcomes :
                return ToolOut (f"# web_search '{query}': no results. Try different terms.")
            lines_p :list [str ]=[f'web_search: {query}']
            rows :list [Row ]=[]
            for result in outcomes :
                url =(getattr (result ,'url','')or '').strip ()
                annotation =(getattr (result ,'note','')or '').strip ()
                if not url or not annotation :
                    continue 
                title =(getattr (result ,'title','')or '').strip ()
                rid_p =str (getattr (result ,'result_id','')or '')
                end =min (len (annotation ),SCOUT_PASSAGE_GLYPHS )
                idx_p =len (rows )
                passage =' '.join (annotation [:end ].split ())
                rows .append (Row (receipt_id =receipt_p ,result_id =rid_p ,note_len =len (annotation ),spans =((0 ,end ),),kind ='search',url =url ,title =title ,preview =passage ))
                lines_p .append (f"[{_SLOT_P.format(idx_p)}] {title}\n    {url}\n    {' '.join(annotation[:end].split())}")
            if not rows :
                return ToolOut (f"# web_search '{query}': no usable results.")
            lines_p .append ('(excerpts only — read_page before relying on any figure)')
            return ToolOut ('\n'.join (lines_p ),rows )

        async def _implement_scan (url :str ,focus_p :str ,query2 :str ,cutoff :float )->ToolOut :
            url =(url or '').strip ()
            if not url :
                return ToolOut ('# read_page: no url')
            if cutoff -monotonic ()<LOWER_REMAINDER_S :
                return ToolOut (f'# read_page {url}: out of time')
            try :
                bundle =await fetch_page (url ,provider =SCOUT_PROVIDER ,timeout =PULL_LIMIT2_S )
            except Exception as exc_p :
                return ToolOut (f'# read_page {url} failed ({_err_p(exc_p)}). Try another source or search for a mirror.')
            outcomes =tuple (getattr (bundle ,'results',())or ())
            receipt_p =getattr (bundle ,'receipt_id','')or ''
            if not outcomes :
                return ToolOut (f'# read_page {url}: no content returned.')
            result =outcomes [0 ]
            annotation =getattr (result ,'note','')or ''
            if not annotation .strip ():
                return ToolOut (f'# read_page {url}: empty page.')
            title =(getattr (result ,'title','')or '').strip ()
            rid_p =str (getattr (result ,'result_id','')or '')
            lexemes =_lexemes (focus_p )|_lexemes (query2 )
            head_end_p =min (len (annotation ),FOLIO2_HEAD_GLYPHS )
            spans =[(0 ,head_end_p )]
            for start ,end in _dense_panes (annotation [head_end_p :],lexemes ,FOLIO2_PANE_GLYPHS ,FOLIO2_PANES ):
                spans .append ((head_end_p +start ,head_end_p +end ))
            spans =list (_merge_reaches (tuple (spans )))
            slot =Row (receipt_id =receipt_p ,result_id =rid_p ,note_len =len (annotation ),spans =tuple (spans ),kind ='page',url =url ,title =title ,preview ='\n'.join ((annotation [s_p :e_p ]for s_p ,e_p in spans ))[:FOLIO2_GLIMPSE_GLYPHS ])
            body_p =[f'read_page [{_SLOT_P.format(0)}] {title or url}\n{url}']
            for i_p ,(start ,end )in enumerate (spans ):
                label_p ='HEAD'if start ==0 else f'REGION @{start}'
                body_p .append (f'--- {label_p} ---\n{annotation[start:end]}')
            if len (annotation )>sum ((e_p -s_p for s_p ,e_p in spans )):
                body_p .append (f'(page is {len(annotation)} chars; {len(spans)} region(s) shown. read_page again with a different focus to see elsewhere.)')
            return ToolOut ('\n'.join (body_p ),[slot ])

        def _invoke_name (invoke :object )->str :
            name_p =getattr (invoke ,'name',None )
            if isinstance (name_p ,str )and name_p .strip ():
                return name_p .strip ()
            fn_p =getattr (invoke ,'function',None )
            return (getattr (fn_p ,'name','')or '').strip ()

        def _invoke_args (invoke :object )->dict :
            crude =getattr (invoke ,'arguments',None )
            if crude is None :
                fn_p =getattr (invoke ,'function',None )
                crude =getattr (fn_p ,'arguments',None )
            if isinstance (crude ,Mapping ):
                return dict (crude )
            if isinstance (crude ,str ):
                try :
                    parsed_p =json .loads (crude or '{}')
                except Exception :
                    return {}
                return parsed_p if isinstance (parsed_p ,dict )else {}
            return {}

        async def _drive_implement (invoke :object ,query2 :str ,cutoff :float )->ToolOut |str :
            name_p =_invoke_name (invoke )
            args_p =_invoke_args (invoke )
            try :
                if name_p =='web_search':
                    return await _implement_scout (str (args_p .get ('query')or ''),cutoff )
                if name_p =='read_page':
                    return await _implement_scan (str (args_p .get ('url')or ''),str (args_p .get ('focus')or ''),query2 ,cutoff )
            except Exception as exc_p :
                return f'# tool {name_p} crashed: {_err_p(exc_p)}'
            return f'# unknown tool: {name_p}'

        def _err_p (exc_p :BaseException )->str :
            try :
                return repr (exc_p )[:160 ]
            except Exception :
                return 'error'

        def _text_of_p (bundle :object )->str :
            llm_p =getattr (bundle ,'llm',None )
            text =(getattr (llm_p ,'raw_text',None )or '').strip ()
            if text :
                return text 
            choices_p =getattr (llm_p ,'choices',None )or []
            if choices_p :
                content_p =getattr (getattr (choices_p [0 ],'message',None ),'content',None )
                if isinstance (content_p ,str ):
                    return content_p .strip ()
            return ''

        async def _dialogue (system_p :str ,user_p :str ,*,timeout :float ,max_tokens :int =2600 ,think :bool =False ,model :str ='')->str :
            messages =[{'role':'system','content':system_p },{'role':'user','content':user_p }]
            for rung_p ,attempts_p in _ladder_p (model or MODEL_ORBIT ):
                for _ in range (attempts_p ):
                    if timeout <=4.0 :
                        return ''
                    try :
                        bundle =await llm_chat (provider =LLM_PROVIDER_P ,model =rung_p ,messages =messages ,temperature =0.15 ,max_output_tokens =max_tokens ,timeout =timeout ,thinking =_deliberate_for (rung_p ,want =think ))
                        text =_text_of_p (bundle )
                        if text :
                            return text 
                    except Exception :
                        continue 
            return ''

        async def _tick (messages :list [dict ],cutoff :float ,*,tools_on :bool ):
            for rung_p ,attempts_p in _ladder_p (MODEL_ORBIT ):
                for _ in range (attempts_p ):
                    timeout =min (TICK_LIMIT2_S ,cutoff -monotonic ()-5.0 )
                    if timeout <=5.0 :
                        return None 
                    try :
                        return await llm_chat (provider =LLM_PROVIDER_P ,model =rung_p ,messages =messages ,tools =IMPLEMENT_SPECS if tools_on else None ,tool_choice ='auto'if tools_on else None ,temperature =0.2 ,thinking =_deliberate_for (rung_p ,want =True ),timeout =timeout )
                    except Exception :
                        continue 
            return None 
        _IMPLEMENT_MARKUP_RE =re .compile ('<\\s*/?\\s*tool_call|<\\s*/?\\s*(?:arg_key|arg_value|function_call|invoke)\\b|\\bweb_search\\s*[（(]\\s*query|\\bread_page\\s*[（(]\\s*url',re .I )
        _MONOLOGUE_RE =re .compile ("^\\s*(?:i (?:need|will|should|am going|'ll)\\b|let me\\b|first,?\\s*(?:i|let)\\b|i'?ll (?:search|look|start|begin|gather|check)|now (?:i|that i)\\b)",re .I )
        _REFUSAL_RE_P =re .compile ("^\\s*(?:i\\s+(?:can(?:no|')t|am\\s+unable|was\\s+unable|do\\s*n[o']t\\s+have)|unable\\s+to\\b|sorry\\b|regrettably\\b|there\\s+is\\s+insufficient)",re .I )
        _TAG_RE =re .compile ('\\[[0-9]{1,3}\\]')
        _VOUCH_RE =re .compile ('\\s*\\((?:verify|unverified|uncertain)[^)]*\\)',re .I )
        LOWER_VERDICT_GLYPHS =40 
        LOWER_TAGGED_GLYPHS =6 

        def _repetitive_p (text :str )->bool :
            parts_p =[p_p .strip ()for p_p in re .split ('(?<=[.!?])\\s+',text or '')if len (p_p .strip ())>20 ]
            if len (parts_p )<3 :
                return False 
            return len (set (parts_p ))<=max (1 ,len (parts_p )//3 )

        def _viable (text :str )->bool :
            body_p =(text or '').strip ()
            if not body_p :
                return False 
            if _IMPLEMENT_MARKUP_RE .search (body_p )or _repetitive_p (body_p ):
                return False 
            if body_p .startswith ('{')or body_p .startswith ('['):
                try :
                    parsed_p =json .loads (body_p )
                    if isinstance (parsed_p ,dict )and ('name'in parsed_p or 'tool'in parsed_p ):
                        return False 
                except Exception :
                    pass 
            tagged =bool (_TAG_RE .search (body_p ))
            if tagged and len (body_p )>=LOWER_TAGGED_GLYPHS :
                return True 
            if _MONOLOGUE_RE .match (body_p )or _REFUSAL_RE_P .match (body_p ):
                return False 
            return len (body_p )>=LOWER_VERDICT_GLYPHS 
        REWORK_EDICT ='That was not a usable final answer — it was tool-call markup, a description of what you intended to do, or empty. Write the answer itself now: plain prose, the direct answer in the first sentence, [n] on every supported claim. Do not call any tool and do not describe your process.'

        def _finale (seconds_remain :float )->str :
            return f'TIME: about {int(max(0, seconds_remain))}s remain. Stop researching and write the final answer NOW from the evidence already in this transcript. Commit to the best supported answer — an unhedged answer with citations beats a hedge. Apply every answer rule you were given and place [n] on every claim.'
        DOSSIER_SYSTEM ='Answer from your own knowledge, then say how to verify it. Two blocks, nothing else.\nDRAFT: your best answer now, with any figure you are unsure of marked (verify).\nPLAN: the specific documents or tables that would confirm it, and the exact search terms that would find them. Name the source the question specifies if it names one.'

        async def _dossier (query2 :str ,cutoff :float )->str :
            timeout =min (DOSSIER_LIMIT2_S ,cutoff -monotonic ()-SEAL_BUFFER_S )
            if timeout <=6.0 :
                return ''
            text =await _dialogue (DOSSIER_SYSTEM ,query2 ,timeout =timeout ,max_tokens =1400 )
            if not text :
                return ''
            return 'PRIOR KNOWLEDGE (unverified — confirm or refute against sources; a (verify) mark means you must check it):\n'+text [:6000 ]
        _SOW_TOKEN_RE =re .compile ("[A-Za-z0-9][\\w.'\\-]{1,}")
        _SOW_STOP =frozenset ('what which who whom whose when where how many much name list give tell show find identify please could would you your the and for with from that this have has was were are is been its their there according per listed'.split ())

        def _sow_queries (query2 :str ,ensemble_like :bool )->list [str ]:
            tokens_p =[t_p for t_p in _SOW_TOKEN_RE .findall (query2 or '')if t_p .lower ()not in _SOW_STOP and len (t_p )>2 ]
            if not tokens_p :
                return []
            core_p =' '.join (tokens_p [:12 ])
            queries_p =[core_p ]
            if ensemble_like :
                queries_p .append (f"list of {' '.join(tokens_p[:8])}")
            for name_p in _named_provenances (query2 )[:1 ]:
                queries_p .append (f"{' '.join(tokens_p[:8])} {name_p}")
            out_p :list [str ]=[]
            for q_p in queries_p :
                q_p =' '.join (q_p .split ())
                if q_p and q_p not in out_p :
                    out_p .append (q_p )
            return out_p [:UPPER_SOW_QUERIES ]

        async def _presow (query2 :str ,ensemble_like :bool ,vault :Ledger ,cutoff :float )->str :
            queries_p =_sow_queries (query2 ,ensemble_like )
            if not queries_p or cutoff -monotonic ()<SEAL_BUFFER_S +12.0 :
                return ''
            outs_p =await asyncio .gather (*(_implement_scout (q_p ,cutoff )for q_p in queries_p ),return_exceptions =True )
            slabs :list [str ]=[]
            for out_p in outs_p :
                if isinstance (out_p ,BaseException )or not isinstance (out_p ,ToolOut ):
                    continue 
                body_p =_seal (out_p ,vault )
                if body_p and (not body_p .startswith ('#')):
                    slabs .append (body_p )
            if not slabs :
                return ''
            return 'SEED EVIDENCE (already retrieved; cite by [n], read_page before relying on a figure):\n'+'\n\n'.join (slabs )

        async def _orbit (query2 :str ,statute :list [str ],dossier :str ,vault :Ledger ,cutoff :float )->tuple [str ,list [dict ]]:
            messages :list [dict ]=[{'role':'system','content':ORBIT_STATUTE }]
            for statute2 in statute :
                messages .append ({'role':'system','content':statute2 })
            if dossier :
                messages .append ({'role':'system','content':dossier })
            seeded_p =await _presow (query2 ,_wants_ensemble (query2 ),vault ,cutoff )
            if seeded_p :
                messages .append ({'role':'system','content':seeded_p })
            messages .append ({'role':'user','content':query2 })
            verdictp =''
            repairs_p =UPPER_REPAIRS 
            ordered_p =False 
            for tick in range (1 ,UPPER_TICKS +1 ):
                remain =cutoff -monotonic ()
                if remain <=LOWER_REMAINDER_S :
                    break 
                seal_now =remain <=SEAL_BUFFER_S or tick >=UPPER_TICKS 
                if (seal_now or tick >=UPPER_TICKS -1 )and (not ordered_p ):
                    messages .append ({'role':'system','content':_finale (remain )})
                    ordered_p =True 
                bundle =await _tick (messages ,cutoff ,tools_on =not seal_now )
                if bundle is None :
                    break 
                llm_p =getattr (bundle ,'llm',None )
                choices_p =getattr (llm_p ,'choices',None )or []
                if not choices_p :
                    break 
                msg_p =getattr (choices_p [0 ],'message',None )
                invokes =tuple (getattr (msg_p ,'tool_calls',None )or ())
                if not invokes :
                    nominee =_text_of_p (bundle )
                    if not _viable (nominee ):
                        if repairs_p >0 and cutoff -monotonic ()>LOWER_REMAINDER_S +10.0 :
                            repairs_p -=1 
                            messages .append ({'role':'system','content':REWORK_EDICT })
                            continue 
                        break 
                    verdictp =nominee 
                    messages .append ({'role':'assistant','content':verdictp })
                    break 
                try :
                    messages .append (msg_p .to_input_message ())
                except Exception :
                    messages .append ({'role':'assistant','content':'','tool_calls':[{'id':getattr (c_p ,'id',''),'type':'function','function':{'name':_invoke_name (c_p ),'arguments':json .dumps (_invoke_args (c_p ))}}for c_p in invokes ]})
                drive =invokes [:UPPER_INVOKES_PER_TICK ]
                ration =max (5.0 ,min (PULL_LIMIT2_S *2 +6.0 ,cutoff -monotonic ()-LOWER_REMAINDER_S ))
                tasks_p =[asyncio .ensure_future (_drive_implement (c_p ,query2 ,cutoff ))for c_p in drive ]
                try :
                    await asyncio .wait (tasks_p ,timeout =ration )
                except Exception :
                    pass 
                outs_p :list [object ]=[]
                for task_p in tasks_p :
                    if task_p .done ():
                        try :
                            outs_p .append (task_p .result ())
                        except Exception as exc_p :
                            outs_p .append (f'# tool crashed: {_err_p(exc_p)}')
                    else :
                        task_p .cancel ()
                        outs_p .append ('# tool timed out — use what you already have')
                for invoke ,out_p in zip (drive ,outs_p ):
                    messages .append ({'role':'tool','tool_call_id':getattr (invoke ,'id',''),'content':_seal (out_p ,vault )})
                for invoke in invokes [UPPER_INVOKES_PER_TICK :]:
                    messages .append ({'role':'tool','tool_call_id':getattr (invoke ,'id',''),'content':'# skipped: per-turn tool budget reached'})
            return (verdictp ,messages )
        INSPECT_SYSTEM ='You are auditing a research answer against the evidence it cites. Report only defects, as short imperative lines, at most eight. Focus on missing members, unsupported figures, wrong units, inverted comparisons, and citations that do not contain the claimed text. Do not rewrite the answer here.'

        async def _inspect (query2 :str ,verdictp :str ,breviary :str ,cutoff :float )->str :
            timeout =min (INSPECT_LIMIT2_S ,cutoff -monotonic ()-LOWER_REMAINDER_S -12.0 )
            if timeout <=6.0 or not verdictp :
                return ''
            user_p =f'QUESTION:\n{query2}\n\nANSWER:\n{verdictp[:14000]}\n\nEVIDENCE:\n{breviary[:40000]}'
            text =await _dialogue (INSPECT_SYSTEM ,user_p ,timeout =timeout ,max_tokens =700 ,model =MODEL_INSPECT )
            body_p =(text or '').strip ()
            if not body_p or body_p .upper ().startswith ('OK'):
                return ''
            return body_p 

        async def _splice (query2 :str ,verdictp :str ,findings_p :str ,breviary :str ,statute :list [str ],cutoff :float )->str :
            timeout =min (SEAL_LIMIT2_S ,cutoff -monotonic ()-LOWER_REMAINDER_S )
            if timeout <=8.0 :
                return verdictp 
            system_p ='Rewrite the answer so every listed defect is fixed. Keep everything that was already correct and cited. Change nothing the findings do not require. Output only the corrected answer.\n\n'+'\n\n'.join (statute )
            user_p =f'QUESTION:\n{query2}\n\nANSWER:\n{verdictp[:14000]}\n\nDEFECTS TO FIX:\n{findings_p[:3000]}\n\nEVIDENCE:\n{breviary[:40000]}'
            text =(await _dialogue (system_p ,user_p ,timeout =timeout ,max_tokens =3000 ,think =True ,model =MODEL_INSPECT )).strip ()
            if not _viable (text ):
                return verdictp 
            before_p =len (set (_tagged_indexes2 (verdictp ,999 )))
            after_p =len (set (_tagged_indexes2 (text ,999 )))
            if before_p and after_p <before_p :
                return verdictp 
            return text 
        BREVIARY_GLYPH_LID =70000 

        def _breviary (vault :Ledger )->str :
            parts_p :list [str ]=[]
            spent_p =0 
            for i_p ,slot in enumerate (vault .rows ,start =1 ):
                text =(slot .preview or '').strip ()
                if not text :
                    continue 
                head_p =f"[{i_p}] {slot.title or ''} ({slot.url or ''})".strip ()
                slab =f'{head_p}\n{text}'
                if spent_p +len (slab )>BREVIARY_GLYPH_LID :
                    break 
                spent_p +=len (slab )
                parts_p .append (slab )
            return '\n\n'.join (parts_p )
        SEAL_SYSTEM ='Write the final answer to the question using ONLY the numbered evidence below. Lead with the direct answer, then the proof. Put [n] on every claim that rests on evidence n. Do not describe your process and do not hedge a fact the evidence establishes.'

        async def _seal_from_breviary (query2 :str ,breviary :str ,statute :list [str ],rough :str ,cutoff :float )->str :
            timeout =min (SEAL_LIMIT2_S ,cutoff -monotonic ()-LOWER_REMAINDER_S )
            if timeout <=6.0 :
                return ''
            system_p =SEAL_SYSTEM +('\n\n'+'\n\n'.join (statute )if statute else '')
            user_p =f'QUESTION:\n{query2}\n\nEVIDENCE:\n{breviary[:70000]}'
            if rough :
                user_p +=f'\n\nEARLIER DRAFT (may be incomplete; verify against the evidence):\n{rough[:4000]}'
            text =await _dialogue (system_p ,user_p ,timeout =timeout ,max_tokens =3000 )
            return text .strip ()if _viable (text )else ''
        _OPENER_RE =re .compile ('^\\s*(?:based on (?:my|the)\\b|now (?:i|that i)\\b|i (?:now )?(?:have|will)\\b|let me\\b)',re .I )

        def _shear_monologue (verdictp :str )->str :
            parts_p =re .split ('(?<=[.!?])\\s+',verdictp or '')
            while len (parts_p )>1 and _OPENER_RE .match (parts_p [0 ])and (not _TAG_RE .search (parts_p [0 ])):
                parts_p =parts_p [1 :]
            return ' '.join (parts_p ).strip ()

        def _safety (query2 :str ,breviary :str )->str :
            lines_p =[ln_p .strip ()for ln_p in (breviary or '').splitlines ()if ln_p .strip ()]
            kept_p :list [str ]=[]
            for line_p in lines_p :
                if line_p .startswith (('#','---','('))or line_p .startswith ('http'):
                    continue 
                if re .match ('^(?:web_search|read_page)\\b',line_p ):
                    continue 
                if len (line_p )<40 or not re .search ('[.!?]',line_p ):
                    continue 
                kept_p .append (line_p )
                if len (kept_p )>=6 :
                    break 
            if not kept_p :
                return 'The available sources did not yield a verifiable answer to this question within the research budget.'
            return 'Based on the retrieved sources, the most relevant established facts are below; they bear directly on the question but were not resolved into a single verified answer within the research budget.\n\n'+'\n'.join ((f'- {ln_p}'for ln_p in kept_p ))
        _TAG_GROUP_RE =re .compile ('\\[([0-9][0-9,\\s\\-]*)\\]')

        def _tagged_indexes2 (verdictp :str ,limit_p :int )->list [int ]:
            out_p :list [int ]=[]
            seen_p :set [int ]=set ()
            for m_p in _TAG_GROUP_RE .finditer (verdictp or ''):
                for part_p in re .split ('[,\\s]+',m_p .group (1 )):
                    part_p =part_p .strip ()
                    if not part_p :
                        continue 
                    if '-'in part_p :
                        bounds_p =part_p .split ('-',1 )
                        try :
                            lo_p ,hi_p =(int (bounds_p [0 ]),int (bounds_p [1 ]))
                        except ValueError :
                            continue 
                        reach =range (lo_p ,hi_p +1 )if lo_p <=hi_p else range (hi_p ,lo_p +1 )
                    else :
                        try :
                            reach =[int (part_p )]
                        except ValueError :
                            continue 
                    for n_p in reach :
                        if 1 <=n_p <=limit_p and n_p not in seen_p :
                            seen_p .add (n_p )
                            out_p .append (n_p )
            return out_p 

        def _footnotes (verdictp :str ,vault :Ledger )->list [CitationRef ]:
            refs_p :list [CitationRef ]=[]
            spent_p =0 
            for n_p in _tagged_indexes2 (verdictp ,len (vault .rows )):
                if len (refs_p )>=FOOTNOTE_LID :
                    break 
                ref =vault .ref (n_p )
                if ref is None :
                    continue 
                cost =vault .cost (n_p )
                if spent_p +cost >SPECIMEN_GLYPH_RATION :
                    continue 
                spent_p +=cost 
                refs_p .append (ref )
            return refs_p 
        OUTLINE2_SYSTEM ='Convert the answer into a JSON value matching the schema. Emit the bare JSON value only — no prose, no markdown fence, no explanation.'

        def _lift_json (text :str )->object |None :
            body_p =(text or '').strip ()
            if body_p .startswith ('```'):
                body_p =re .sub ('^```[a-zA-Z]*\\s*|\\s*```$','',body_p ).strip ()
            try :
                return json .loads (body_p )
            except Exception :
                pass 
            for opener_p ,closer_p in (('{','}'),('[',']')):
                start ,end =(body_p .find (opener_p ),body_p .rfind (closer_p ))
                if 0 <=start <end :
                    try :
                        return json .loads (body_p [start :end +1 ])
                    except Exception :
                        continue 
            return None 

        def _outline2_skeleton (outline2 :object )->object :
            if not isinstance (outline2 ,dict ):
                return None 
            kind =outline2 .get ('type')
            if isinstance (kind ,list ):
                kind =next ((k for k in kind if k !='null'),None )
            if kind =='object':
                props_p =outline2 .get ('properties')
                return {k :_outline2_skeleton (v_p )for k ,v_p in props_p .items ()}if isinstance (props_p ,dict )else {}
            if kind =='array':
                return []
            if kind in ('number','integer'):
                return 0 
            if kind =='boolean':
                return False 
            return ''

        async def _structured_p (query2 :str ,outline2 :object ,verdictp :str ,cutoff :float )->object :
            timeout =min (40.0 ,cutoff -monotonic ()-3.0 )
            if timeout >6.0 :
                user_p =f"SCHEMA:\n{json.dumps(outline2)[:4000]}\n\nQUESTION:\n{query2}\n\nANSWER:\n{(verdictp or '')[:8000]}"
                for _ in range (2 ):
                    text =await _dialogue (OUTLINE2_SYSTEM ,user_p ,timeout =timeout ,max_tokens =1200 ,model =MODEL_INSPECT )
                    value_p =_lift_json (text )
                    if value_p is not None :
                        return value_p 
                    timeout =min (timeout ,cutoff -monotonic ()-3.0 )
                    if timeout <=6.0 :
                        break 
            return _outline2_skeleton (outline2 )
        FINAL2_FAILURES :list [str ]=[]

        def _record_mishap (where_p :str ,exc_p :BaseException )->None :
            try :
                FINAL2_FAILURES .append (f'{where_p}: {_err_p(exc_p)}')
                FINAL2_FAILURES [:]=FINAL2_FAILURES [-5 :]
            except Exception :
                pass 

        async def _resolve2 (query2 :str ,cutoff :float )->tuple [str ,Ledger ]:
            vault =Ledger ()
            statute =_contour_statute (query2 )
            dossier =await _dossier (query2 ,cutoff )
            verdictp ,_messages_p =await _orbit (query2 ,statute ,dossier ,vault ,cutoff )
            breviary =_breviary (vault )
            if not verdictp and breviary :
                verdictp =await _seal_from_breviary (query2 ,breviary ,statute ,'',cutoff )
            if verdictp and breviary and (cutoff -monotonic ()>LOWER_REMAINDER_S +24.0 ):
                findings_p =await _inspect (query2 ,verdictp ,breviary ,cutoff )
                if findings_p :
                    verdictp =await _splice (query2 ,verdictp ,findings_p ,breviary ,statute ,cutoff )
            if not _viable (verdictp ):
                verdictp =_safety (query2 ,breviary )
            verdictp =_shear_monologue (_VOUCH_RE .sub ('',verdictp ))[:VERDICT_GLYPH_LID ]
            return (verdictp ,vault )

        async def query (query :Query )->Response :
            cutoff =monotonic ()+WALL_RATION_S 
            query2 =(getattr (query ,'text','')or '').strip ()
            if not query2 :
                return Response (text ='No question provided.')
            outline2 =getattr (query ,'output_schema',None )
            try :
                verdictp ,vault =await _resolve2 (query2 ,cutoff )
            except Exception as exc_p :
                _record_mishap ('solve',exc_p )
                verdictp ,vault =('',Ledger ())
            try :
                citations =_footnotes (verdictp ,vault )
            except Exception :
                citations =[]
            if outline2 is None :
                if not verdictp :
                    verdictp ='The available sources did not yield a verifiable answer to this question within the research budget.'
                return Response (text =verdictp ,citations =citations or None )
            try :
                value_p =await _structured_p (query2 ,outline2 ,verdictp ,cutoff )
            except Exception :
                value_p =_outline2_skeleton (outline2 )
            try :
                return Response (output =value_p ,citations =citations or None )
            except Exception :
                return Response (output =value_p )
        return query 


class HardnessSwitcher :
    _PROVIDER ='chutes'
    _MODEL ='google/gemma-4-31B-turbo-TEE'
    _PROMPT ='Is this question easy or hard? Reply with one word: easy or hard.'
    _TIMEOUT_S =6.0 

    async def _is_easy (self ,text :str )->bool :
        result =await asyncio .wait_for (llm_chat (provider =self ._PROVIDER ,model =self ._MODEL ,messages =[{'role':'system','content':self ._PROMPT },{'role':'user','content':text }],temperature =0.0 ,max_output_tokens =4 ,thinking =LlmThinkingConfig (enabled =False ),timeout =self ._TIMEOUT_S ),timeout =self ._TIMEOUT_S +2.0 )
        return (result .response .raw_text or '').strip ().lower ().startswith ('easy')


_LIGHT_DRIVE =LightCorridor ()._compile ()
_HEAVY_DRIVE =HeavyCorridor ()._compile ()
_SWITCHER =HardnessSwitcher ()

async def _s17_base_query(query: Query) -> Response:
    try :
        light =await _SWITCHER ._is_easy (query .text )
    except Exception :
        light =False 
    if light :
        return await _LIGHT_DRIVE (query )
    return await _HEAVY_DRIVE (query )


# =====================================================================
# submittion17 MECHANISM — iterative claim-driven retrieval and
# verification loop (decompose -> per-claim targeted search -> per-claim
# verdict -> bounded sequential patch), independent of internal evidence
# =====================================================================
#
# Runs after the base pipeline above has produced a draft Response. Unlike
# a single fresh-evidence spot-check, this stage:
#   1. Decomposes the draft into up to 4 discrete, independently-checkable
#      load-bearing/time-sensitive factual claims (LLM call).
#   2. Issues ONE NEW, independently targeted search_web call PER CLAIM
#      (concurrently), each query built from that specific claim rather
#      than the original question -- retrieval targeted at verifying
#      individual assertions, not a single whole-answer check.
#   3. Verifies each claim against only its own freshly retrieved,
#      independently sourced evidence, additionally flagging claims whose
#      fresh sources internally disagree with each other ("disputed").
#   4. Sequentially, per claim: a contradicted claim triggers a bounded
#      corrective rewrite of the running answer (grounded in that claim's
#      fresh evidence only); a disputed claim gets a brief inline
#      qualifier noting source disagreement; a corroborated claim
#      reinforces citation coverage with new, distinct CitationRef entries
#      (never fabricated -- always drawn from a real receipt_id/result_id
#      this pass itself retrieved).
# This changes decomposition, retrieval targeting, contradiction handling,
# verification, and citation-provenance control flow relative to the base
# pipeline; it is not a prompt or parameter tweak. Any failure, missing
# evidence, structured/schema response, or time shortage is a strict
# no-op that returns the base pipeline's own response (after cheap exact
# duplicate-citation cleanup only).

import asyncio as _s17_asyncio
import json as _s17_json
import re as _s17_re
from time import monotonic as _s17_monotonic

_S17_HARD_BUDGET_GATE_S = 250.0
_S17_MAX_WINDOW_S = 45.0
_S17_MIN_WINDOW_S = 8.0
_S17_DECOMPOSE_TIMEOUT_S = 9.0
_S17_SEARCH_TIMEOUT_S = 9.0
_S17_VERIFY_TIMEOUT_S = 8.0
_S17_PATCH_TIMEOUT_S = 11.0
_S17_MAX_CLAIMS = 4
_S17_MAX_NEW_CITATIONS_PER_CLAIM = 2
_S17_MAX_TOTAL_CITATIONS = 60
_S17_MODEL = "deepseek/deepseek-v3.2"

_S17_DECOMPOSE_SYSTEM_PROMPT = (
    "You extract independently fact-checkable claims from a research answer.\n"
    "Given a question and a drafted answer, list up to 4 discrete, concrete, "
    "load-bearing or time-sensitive factual claims from the answer that are "
    "worth independently re-verifying (specific names, dates, figures, "
    "statuses, rankings, outcomes). Skip vague, stylistic, or trivially "
    "well-known statements.\n"
    "For each claim, also produce a short, targeted web search query (5-12 "
    "words) that would directly test whether that specific claim is true -- "
    "not a restatement of the whole original question.\n"
    "Return JSON only: {\"claims\": [{\"claim\": str, \"search_query\": str}, ...]}. "
    "Return an empty list if the answer has no such claims."
)

_S17_VERIFY_SYSTEM_PROMPT = (
    "You are a strict fact-verification auditor for ONE specific claim.\n"
    "You receive a single claim and up to 4 freshly retrieved, independent "
    "evidence snippets gathered specifically to test that claim.\n"
    "Classify strictly from this evidence:\n"
    "- contradicted: a snippet states a directly conflicting fact (different "
    "name, date, figure, status, or outcome) for the same element the claim "
    "asserts.\n"
    "- corroborated: one or more snippets directly support the claim.\n"
    "- disputed: two or more snippets disagree with EACH OTHER on the same "
    "element the claim addresses (not just with the claim).\n"
    "- unverifiable: the evidence neither supports, conflicts, nor disputes.\n"
    "Return JSON only with keys: verdict "
    "('contradicted'|'corroborated'|'disputed'|'unverifiable'), "
    "correction (string or null, only for contradicted -- the corrected "
    "fact), dispute_note (string or null, only for disputed -- one short "
    "clause describing the disagreement), supporting_snippet_indices "
    "(array of 0-based ints, may be empty)."
)

_S17_PATCH_SYSTEM_PROMPT = (
    "You correct ONE factual claim inside a research answer using freshly "
    "retrieved evidence that specifically contradicts it.\n"
    "Rewrite the COMPLETE answer: keep every part unrelated to this claim "
    "byte-for-byte where feasible, and replace only the conflicting fact "
    "with what the fresh evidence supports. If the evidence only shows the "
    "old claim is unverified rather than the correct value, soften the "
    "claim to note it is unconfirmed instead of guessing a new value.\n"
    "Preserve all existing citation markers whose underlying claims are "
    "unchanged. Output plain answer text only: no preamble, no markdown "
    "fences, no meta-commentary about the correction process."
)


def _s17_strip_json_fences(raw: str) -> str:
    return _s17_re.sub(r"^```(?:json)?\s*|\s*```$", "", raw or "", flags=_s17_re.I | _s17_re.M).strip()


def _s17_chat_text(llm_result) -> str:
    if llm_result is None:
        return ""
    resp = getattr(llm_result, "response", None)
    text = getattr(resp, "raw_text", None) if resp is not None else None
    return (text or "").strip()


def _s17_citation_key(ref) -> tuple:
    slices = tuple(
        (getattr(sl, "start", None), getattr(sl, "end", None))
        for sl in (getattr(ref, "slices", None) or [])
    )
    return (getattr(ref, "receipt_id", None), getattr(ref, "result_id", None), slices)


def _s17_dedup_citations(response):
    citations = getattr(response, "citations", None)
    if not citations:
        return response
    seen: set = set()
    deduped = []
    for ref in citations:
        key = _s17_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    if len(deduped) == len(citations):
        return response
    try:
        return response.model_copy(update={"citations": deduped})
    except Exception:
        return response


def _s17_merge_citations(existing, new_refs):
    existing_list = list(existing or [])
    seen = {_s17_citation_key(ref) for ref in existing_list}
    merged = list(existing_list)
    for ref in new_refs:
        key = _s17_citation_key(ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(ref)
        if len(merged) >= _S17_MAX_TOTAL_CITATIONS:
            break
    return merged


async def _s17_decompose_claims(question: str, answer: str) -> list:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_DECOMPOSE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question:\n{question}\n\nDrafted answer:\n{answer[:12000]}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=500,
            timeout=_S17_DECOMPOSE_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return []
    try:
        parsed = _s17_json.loads(_s17_strip_json_fences(_s17_chat_text(result)))
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw_claims = parsed.get("claims")
    if not isinstance(raw_claims, list):
        return []
    out = []
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim") or "").strip()
        squery = str(item.get("search_query") or "").strip()
        if claim and squery:
            out.append({"claim": claim, "search_query": squery})
        if len(out) >= _S17_MAX_CLAIMS:
            break
    return out


async def _s17_search_claim(search_query: str):
    from harnyx_miner_sdk.api import search_web as _s17_search_web

    for provider_name in ("parallel", "desearch"):
        try:
            payload = await _s17_search_web(
                search_query[:300],
                provider=provider_name,
                num=4,
                timeout=_S17_SEARCH_TIMEOUT_S,
            )
        except Exception:
            payload = None
        if payload is None:
            continue
        results = list(getattr(payload, "results", None) or [])
        if not results:
            continue
        receipt = str(getattr(payload, "receipt_id", "") or "")
        if not receipt:
            continue
        items = []
        for item in results:
            rid = getattr(item, "result_id", None)
            note = (getattr(item, "note", None) or "").strip()
            if not isinstance(rid, str) or not rid or not note:
                continue
            items.append({
                "result_id": rid,
                "note": note,
                "title": (getattr(item, "title", None) or "").strip(),
                "url": (getattr(item, "url", None) or "").strip(),
            })
            if len(items) >= 4:
                break
        if items:
            return {"receipt_id": receipt, "items": items}
    return None


async def _s17_verify_claim(claim: str, evidence_items: list) -> dict:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    evidence_block = "\n".join(
        f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
        for idx, item in enumerate(evidence_items)
    )
    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_VERIFY_SYSTEM_PROMPT},
                {"role": "user", "content": f"Claim:\n{claim}\n\nFresh evidence snippets:\n{evidence_block}"},
            ],
            tools=None,
            temperature=0.0,
            max_output_tokens=350,
            timeout=_S17_VERIFY_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return {"verdict": "unverifiable"}
    try:
        report = _s17_json.loads(_s17_strip_json_fences(_s17_chat_text(result)))
    except Exception:
        return {"verdict": "unverifiable"}
    if not isinstance(report, dict):
        return {"verdict": "unverifiable"}
    return report


def _s17_build_refs(receipt_id: str, evidence_items: list, indices) -> list:
    from harnyx_miner_sdk.query import CitationRef as _s17_citation_ref
    from harnyx_miner_sdk.query import CitationSlice as _s17_citation_slice

    refs = []
    for raw_idx in (indices or []):
        try:
            idx = int(raw_idx)
        except Exception:
            continue
        if not (0 <= idx < len(evidence_items)):
            continue
        item = evidence_items[idx]
        note_len = len(item["note"])
        end = min(500, note_len)
        if end <= 0:
            continue
        try:
            refs.append(_s17_citation_ref(
                receipt_id=receipt_id,
                result_id=item["result_id"],
                slices=[_s17_citation_slice(start=0, end=end)],
            ))
        except Exception:
            continue
        if len(refs) >= _S17_MAX_NEW_CITATIONS_PER_CLAIM:
            break
    return refs


async def _s17_patch_claim(question: str, answer: str, claim: str, correction: str, evidence_block: str) -> str:
    from harnyx_miner_sdk.api import llm_chat as _s17_llm_chat

    prompt = (
        f"Question:\n{question}\n\n"
        f"Current answer:\n{answer[:12000]}\n\n"
        f"Claim being corrected:\n{claim}\n\n"
        f"What the fresh evidence supports instead:\n{correction or 'see evidence below'}\n\n"
        f"Fresh evidence snippets:\n{evidence_block}"
    )
    try:
        result = await _s17_llm_chat(
            provider="openrouter",
            model=_S17_MODEL,
            messages=[
                {"role": "system", "content": _S17_PATCH_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.1,
            max_output_tokens=1400,
            timeout=_S17_PATCH_TIMEOUT_S,
            thinking={"enabled": False},
        )
    except Exception:
        return ""
    return _s17_chat_text(result)[:79000].strip()


async def _s17_verify_and_patch(_s17_query, _s17_response):
    _s17_response = _s17_dedup_citations(_s17_response)
    if getattr(_s17_response, "output", None) is not None:
        return _s17_response
    question = (getattr(_s17_query, "text", None) or "").strip()
    answer = (getattr(_s17_response, "text", None) or "").strip()
    if not question or not answer:
        return _s17_response

    claims = await _s17_decompose_claims(question, answer)
    if not claims:
        return _s17_response

    search_results = await _s17_asyncio.gather(
        *[_s17_search_claim(c["search_query"]) for c in claims],
        return_exceptions=True,
    )

    per_claim = []
    for claim_info, search_result in zip(claims, search_results):
        if isinstance(search_result, Exception) or not search_result:
            continue
        per_claim.append((claim_info, search_result))
    if not per_claim:
        return _s17_response

    verify_results = await _s17_asyncio.gather(
        *[_s17_verify_claim(ci["claim"], sr["items"]) for ci, sr in per_claim],
        return_exceptions=True,
    )

    running_answer = answer
    all_new_refs = []
    appended_notes = []
    for (claim_info, search_result), verdict_report in zip(per_claim, verify_results):
        if isinstance(verdict_report, Exception) or not isinstance(verdict_report, dict):
            continue
        verdict = str(verdict_report.get("verdict") or "").strip().lower()
        items = search_result["items"]
        receipt_id = search_result["receipt_id"]
        evidence_block = "\n".join(
            f"[{idx}] {item['title']} \u2014 {item['url']}\n{item['note'][:900]}"
            for idx, item in enumerate(items)
        )

        if verdict == "contradicted":
            new_text = await _s17_patch_claim(
                question, running_answer, claim_info["claim"],
                str(verdict_report.get("correction") or ""), evidence_block,
            )
            if new_text:
                running_answer = new_text
                refs = _s17_build_refs(receipt_id, items, verdict_report.get("supporting_snippet_indices") or [0])
                all_new_refs.extend(refs)
            continue

        if verdict == "corroborated":
            indices = verdict_report.get("supporting_snippet_indices")
            refs = _s17_build_refs(receipt_id, items, indices if isinstance(indices, list) and indices else [0])
            all_new_refs.extend(refs)
            continue

        if verdict == "disputed":
            note = str(verdict_report.get("dispute_note") or "").strip()
            if note and len(appended_notes) < 2:
                appended_notes.append(note)
            refs = _s17_build_refs(receipt_id, items, [0])
            all_new_refs.extend(refs)
            continue

    if appended_notes:
        qualifier = " Note: " + "; ".join(appended_notes) + "."
        if len(running_answer) + len(qualifier) <= 79000:
            running_answer = running_answer + qualifier

    merged_citations = _s17_merge_citations(getattr(_s17_response, "citations", None), all_new_refs)
    if running_answer == answer and len(merged_citations) == len(list(getattr(_s17_response, "citations", None) or [])):
        return _s17_response
    try:
        return _s17_response.model_copy(update={"text": running_answer, "citations": merged_citations})
    except Exception:
        return _s17_response


async def _s17_finalize(_s17_query, _s17_response, _s17_t0: float):
    """Bounded, iterative claim-driven retrieval-and-verification pass."""
    if _s17_response is None:
        return _s17_response
    if getattr(_s17_response, "text", None) in (None, "") and getattr(_s17_response, "output", None) is None:
        return _s17_response
    elapsed = _s17_monotonic() - _s17_t0
    if elapsed >= _S17_HARD_BUDGET_GATE_S:
        return _s17_dedup_citations(_s17_response)
    window = min(_S17_MAX_WINDOW_S, max(_S17_MIN_WINDOW_S, 280.0 - elapsed))
    try:
        return await _s17_asyncio.wait_for(
            _s17_verify_and_patch(_s17_query, _s17_response),
            timeout=window,
        )
    except Exception:
        return _s17_dedup_citations(_s17_response)


@entrypoint("query")
async def query(query: Query) -> Response:
    _s17_t0 = _s17_monotonic()
    _s17_resp = await _s17_base_query(query)
    try:
        return await _s17_finalize(query, _s17_resp, _s17_t0)
    except Exception:
        return _s17_resp
