/* ============================================================================
   QUERY: fnLoadCsv                (function)
   ============================================================================ */
let
    fnLoadCsv = (fileName as text) as table =>
        let
            Source = Csv.Document(
                File.Contents(pSourceFolder & "\" & fileName),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
        in
            Promoted
in
    fnLoadCsv
