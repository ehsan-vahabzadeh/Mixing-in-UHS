import re
import unicodedata

def sort_longtable_by_first_column(latex: str) -> str:
    """
    Sorts the data rows (lines ending with '\\\\') of a LaTeX longtable
    alphabetically by the first column (Field Name), while preserving
    the rest of the LaTeX exactly.
    """

    # --- Helper: make a sortable key from the first column ---
    def sort_key(row_line: str) -> str:
        # first column = everything before first &
        first_col = row_line.split("&", 1)[0].strip()

        # remove citations for sorting purposes only
        # e.g. "Frigg \cite{...}" -> "Frigg"
        first_col = re.sub(r"\\cite\{[^}]*\}", "", first_col)

        # remove other LaTeX commands in first column (conservative)
        # e.g. \textit{X} -> X
        first_col = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^}]*)\}", r"\1", first_col)

        # normalize spaces
        first_col = re.sub(r"\s+", " ", first_col).strip()

        # normalize unicode (handles weird accented stuff if it exists)
        first_col = unicodedata.normalize("NFKD", first_col)

        return first_col.casefold()  # case-insensitive

    lines = latex.splitlines(keepends=True)

    # Identify data rows: lines that contain '&' and end with '\\'
    data_idx = []
    data_rows = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "&" in stripped and stripped.endswith(r"\\"):
            data_idx.append(i)
            data_rows.append(line)

    # Sort rows by first column key
    sorted_rows = sorted(data_rows, key=sort_key)

    # Put sorted rows back in the same slots
    out = lines[:]
    for i, new_line in zip(data_idx, sorted_rows):
        out[i] = new_line

    return "".join(out)


if __name__ == "__main__":
    # Paste your longtable LaTeX here (triple quotes)
    latex_table = r"""
\begin{longtable}{p{3cm}p{1.5cm}p{1.5cm}p{1.8cm}p{1.5cm}p{1.8cm}p{1.8cm}}
\caption{UK natural gas reservoir properties, including number of wells, porosity, permeability, pressure, temperature, and recoverable gas initially in place (RGIIP), used in this study.}
\label{tab:full_field_properties}\\
\toprule
                          Field Name &  Number of Wells &  Porosity [-] &  Permeability [mD] &  Pressure [bar] &  Temperature [K] &  RGIIP [$\times$10$^9$ sm$^3$] \\
\midrule
\endfirsthead
\bottomrule
\endlastfoot
Frigg \cite{brewster1991frigg}  &               48 &           0.3 &             1500.0 &           187.2 &               348.3 &              178.0 \\
Barque \cite{CO2Stored2025}  &               25 &           0.1 &               50.0 &           263.7 &               352.1 &               38.7 \\
Amethyst East \cite{garland1991amethyst}  &               19 &           0.2 &              100.0 &           282.7 &               361.1 &               23.9 \\
Camelot North \cite{holmes1991camelot} &                2 &           0.2 &              200.0 &           193.0 &               333.1 &                0.6 \\
Camelot Central South\cite{holmes1991camelot}  &                6 &           0.2 &              200.0 &           193.0 &               333.1 &                7.1 \\
Camelot  Northeast\cite{holmes1991camelot}  &                2 &           0.2 &              200.0 &           193.0 &               333.1 &                0.7 \\
Cleeton\cite{CO2Stored2025}  &                7 &           0.2 &               95.0 &           285.9 &               352.1 &               10.1 \\
Clipper North\cite{CO2Stored2025}  &               25 &           0.1 &               20.0 &           265.4 &               352.1 &               21.3 \\
Corvette\cite{CO2Stored2025}  &                2 &           0.2 &              400.0 &           281.5 &               359.1 &                6.7 \\
Davy\cite{CO2Stored2025}  &                4 &           0.2 &               30.0 &           245.6 &               361.1 &                5.7 \\
Bessemer\cite{CO2Stored2025}  &                3 &           0.2 &               30.0 &           277.8 &               364.1 &                3.7 \\
Beaufort\cite{CO2Stored2025}  &                1 &           0.2 &               30.0 &           275.8 &               364.1 &                0.9 \\
Brown\cite{CO2Stored2025}  &                1 &           0.2 &               30.0 &           273.6 &               362.1 &                0.7 \\
Gawain\cite{CO2Stored2025}  &                3 &           0.2 &              100.0 &           283.9 &               353.1 &                3.8 \\
Guinevere\cite{CO2Stored2025}  &                2 &           0.1 &               20.0 &           275.8 &               365.1 &                2.5 \\
Deborah\cite{CO2Stored2025}  &                4 &           0.1 &               75.0 &           190.0 &               336.1 &                9.8 \\
Big Dotty\cite{CO2Stored2025}  &                5 &           0.2 &              250.0 &           182.3 &               339.1 &                6.3 \\
Little Dotty  (Leman)\cite{CO2Stored2025} &                1 &           0.2 &              450.0 &           189.3 &               336.1 &                5.3 \\
Della\cite{CO2Stored2025}  &                2 &           0.1 &               50.0 &           193.0 &               335.1 &                3.0 \\
Dawn\cite{CO2Stored2025}  &                1 &           0.2 &              170.0 &           162.3 &               337.1 &                0.6 \\
Delilah\cite{CO2Stored2025}  &                1 &           0.1 &               54.0 &           195.6 &               339.1 &               18.4 \\
Indefatigable\cite{CO2Stored2025}  &               47 &           0.1 &               30.0 &           284.2 &               364.1 &              133.0 \\
Johnston\cite{CO2Stored2025}  &                6 &           0.1 &               10.0 &           326.1 &               381.1 &                8.6 \\
Malory\cite{CO2Stored2025}  &                1 &           0.1 &               24.0 &           293.5 &               366.1 &                2.1 \\
Esmond \cite{ketter1991esmond}  &                5 &           0.2 &                1.0 &           157.2 &               334.8 &                8.1 \\
Forbes\cite{ketter1991esmond}  &                2 &           0.2 &                1.0 &           193.0 &               336.1 &                2.2 \\
Gordon \cite{ketter1991esmond} &                2 &           0.2 &                1.0 &           180.8 &               334.1 &                3.9 \\
Caister B\cite{CO2Stored2025}  &                8 &           0.2 &              100.0 &           143.1 &               327.6 &                3.3 \\
Victor\cite{lambert1991victor}  &                6 &           0.2 &               52.0 &           279.0 &               362.1 &               26.1 \\
Vixen\cite{CO2Stored2025,vixen_field}   &                1 &           0.2 &                5.0 &           266.6 &               356.1 &                3.3 \\
West Sole \cite{winter1991west}  &               29 &           0.1 &                3.0 &           294.0 &               358.1 &               39.2 \\
Bure\cite{CO2Stored2025}  &                2 &           0.2 &               78.0 &           255.6 &               353.7 &                1.7 \\
Rough\cite{CO2Stored2025}  &               26 &           0.1 &               75.0 &           312.5 &               365.1 &               10.4 \\
Yare\cite{CO2Stored2025}  &                1 &           0.2 &               60.0 &           251.5 &               354.3 &                1.5 \\
Markham \cite{myres1995markham}  &                6 &           0.1 &               50.0 &           428.3 &               387.1 &               19.8 \\
Vampire\cite{CO2Stored2025}  &                3 &           0.1 &               50.0 &           266.6 &               356.1 &                2.0 \\
Valkyrie\cite{CO2Stored2025}  &                1 &           0.1 &                5.4 &           266.6 &               356.1 &                3.8 \\
Brigantine\cite{CO2Stored2025}  &                0 &           0.1 &               30.0 &           266.6 &               356.1 &               10.0 \\
Babbage \cite{phipps2020babbage}  &                5 &           0.1 &                1.0 &           328.2 &               377.6 &                5.2 \\
Carrack \cite{rieu2020carrack}  &                6 &           0.1 &                1.0 &           346.0 &               368.1 &               12.0 \\
Leman\cite{CO2Stored2025}  &              200 &           0.1 &                4.2 &           208.3 &               325.1 &              361.0 \\
Mercury\cite{CO2Stored2025}  &                2 &           0.1 &               59.0 &           296.6 &               369.1 &                2.3 \\
Neptune\cite{CO2Stored2025}  &                4 &           0.2 &              120.0 &           302.3 &               353.1 &                8.1 \\
Pickerill \cite{werngren2003pickerill}  &               18 &           0.1 &                5.0 &           275.4 &               369.1 &               14.2 \\
North Sean\cite{hillier2003sean}  &                8 &           0.2 &              265.0 &           272.0 &               367.1 &                6.6 \\
South Sean\cite{hillier2003sean}   &                8 &           0.2 &              305.0 &           274.2 &               362.1 &               13.8 \\
East Sean\cite{hillier2003sean}  &                0 &           0.2 &               90.0 &           266.9 &               370.1 &                3.6 \\
    V-fields\cite{CO2Stored2025} &               54 &           0.1 &                5.4 &           251.8 &               344.1 &               46.8 \\
Viking \cite{morgan1991viking} &               21 &           0.1 &               50.0 &           304.0 &               358.1 &               80.1 \\
Anglia\cite{CO2Stored2025}  &               12 &           0.1 &                1.0 &           266.6 &               356.1 &                8.2 \\
Ann\cite{CO2Stored2025}  &                5 &           0.2 &              112.5 &           266.6 &               356.1 &                2.0 \\
Audrey\cite{CO2Stored2025}  &               11 &           0.2 &              112.5 &           266.6 &               356.1 &               25.2 \\
Baird\cite{CO2Stored2025}  &                1 &           0.1 &               30.0 &           266.6 &               356.1 &                4.0 \\
Waveney \cite{bruce2003waveney}  &                2 &           0.1 &               12.0 &           252.0 &               357.1 &                2.4 \\
Bell\cite{CO2Stored2025}  &                1 &           0.2 &              112.0 &           266.6 &               356.1 &                3.2 \\
Callisto\cite{CO2Stored2025}  &                2 &           0.2 &               30.0 &           266.6 &               356.1 &                1.5 \\
Europa\cite{CO2Stored2025}  &                4 &           0.2 &               30.0 &           266.6 &               356.1 &                2.4 \\
Galahad\cite{CO2Stored2025}  &                1 &           0.1 &               20.0 &           266.6 &               356.1 &                4.3 \\
Galleon\cite{CO2Stored2025}  &               22 &           0.1 &                1.0 &           266.6 &               356.1 &               26.7 \\
Ganymede\cite{CO2Stored2025}  &                8 &           0.2 &               30.0 &           266.6 &               356.1 &                7.8 \\
Hyde\cite{steele1993hyde}  &                2 &           0.1 &                1.0 &           297.5 &               360.1 &                4.2 \\
Lancelot\cite{CO2Stored2025}  &                4 &           0.1 &               30.0 &           266.6 &               356.1 &                9.0 \\
Newsham\cite{CO2Stored2025}  &                1 &           0.1 &                3.0 &           266.6 &               356.1 &                1.0 \\
Ravenspurn\cite{heinrich1991ravenspurn}  &               48 &           0.1 &               10.0 &           309.5 &               366.1 &               19.8 \\
Skiff\cite{CO2Stored2025}  &                1 &           0.1 &                1.0 &           267.0 &               356.1 &               10.0 \\
Thames\cite{CO2Stored2025}  &                3 &           0.2 &              250.0 &           255.6 &               356.1 &                6.4 \\
Little Dotty  (Bunter) \cite{hook2020hewett} &                1 &           0.2 &              350.0 &           115.5 &               320.1 &                6.0 \\
Hamilton\cite{CO2Stored2025}  &                4 &           0.1 &              777.5 &            96.8 &               303.1 &               17.8 \\
Hamilton North\cite{CO2Stored2025}  &                3 &           0.1 &              307.5 &           105.8 &               303.1 &                6.5 \\
North Morecambe\cite{bushell1986reservoir}  &               10 &           0.1 &               90.0 &           124.1 &               306.1 &               36.5 \\
South Morecambe\cite{bushell1986reservoir}  &               36 &           0.1 &              150.0 &           128.3 &               305.9 &              155.8 \\
Millom\cite{CO2Stored2025}  &               12 &           0.1 &                0.5 &           113.8 &               304.6 &                7.3 \\
Bains\cite{CO2Stored2025}  &                1 &           0.1 &             1323.0 &           113.8 &               304.6 &                1.3 \\
Dalton\cite{CO2Stored2025}  &                3 &           0.1 &             1323.0 &           113.8 &               304.6 &                1.4 \\
Calder\cite{blow1997calder}  &                2 &           0.1 &             1323.0 &           113.8 &               304.6 &                3.4 \\
Murdoch\cite{moscariello2020ketch}  &               10 &           0.1 &               73.0 &           423.3 &               386.1 &                9.9 \\
Schooner\cite{CO2Stored2025}  &               10 &           0.1 &              100.0 &           446.4 &               383.1 &                8.8 \\
Trent\cite{o2003trent}  &                3 &           0.1 &                0.3 &           379.2 &               385.1 &                2.6 \\
Tyne North\cite{o2003tyne}  &                2 &           0.1 &               35.1 &           424.2 &               389.1 &                2.3 \\
Tyne South\cite{o2003tyne}  &                5 &           0.1 &               48.4 &           436.9 &               390.1 &                1.5 \\
Boulton\cite{conway2003boulton}  &                5 &           0.1 &               73.0 &           447.4 &               389.1 &                4.0 \\
Caister C\cite{CO2Stored2025}  &                5 &           0.1 &                5.0 &           428.3 &               387.1 &                5.3 \\
Hewett\cite{CO2Stored2025}  &               32 &           0.2 &              500.0 &           136.8 &               325.1 &               59.5 \\
Hewett  (Bunter)\cite{CO2Stored2025} &                7 &           0.2 &             1300.0 &            93.9 &               315.1 &               34.6 \\
Hewett (Zechstein)\cite{CO2Stored2025}  &               32 &           0.1 &                1.0 &           147.3 &               327.1 &                5.9 \\
Breagh\cite{nwachukwu2020breagh}  &               10 &           0.1 &               50.0 &           258.1 &               358.1 &               12.9 \\
Cavendish\cite{wasielka2020cavendish}  &                5 &           0.1 &                7.0 &           421.1 &               372.1 &                2.8 \\
Chiswick\cite{smit2020chiswick}  &                2 &           0.1 &                1.5 &           391.9 &               383.1 &                6.2 \\
Cygnus\cite{dredge2020cygnus}  &                8 &           0.1 &                1.0 &           396.9 &               380.1 &               21.1 \\
Ensign\cite{verlinden2020ensign}  &                1 &           0.1 &                0.1 &           275.8 &               353.1 &                0.6 \\
Juliet\cite{offer2020juliet}  &                2 &           0.2 &               60.0 &           286.1 &               366.1 &                0.8 \\
Rhyl\cite{zavala2020rhyl}  &                2 &           0.1 &              500.0 &           149.9 &               311.5 &                4.2 \\
Albury\cite{trueman2003humbly}  &                1 &           0.2 &             1060.0 &            75.8 &               304.8 &                0.1 \\
Saltfleetby\cite{hodge2003saltfleetby}  &                5 &           0.1 &               10.0 &           245.9 &               357.0 &                2.3 \\
Crosby Warren\cite{johnson2020crosby}  &                2 &           0.1 &               10.0 &           169.1 &               331.1 &                0.1 \\
Kirkleatham\cite{EGDON2010}  &                1 &           0.1 &              335.0 &            87.2 &               299.3 &                0.2 \\

\end{longtable}
""".strip("\n")

    print(sort_longtable_by_first_column(latex_table))
