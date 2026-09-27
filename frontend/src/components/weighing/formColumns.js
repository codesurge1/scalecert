// Direction mapping — explicit and intentional, do not "simplify" this away.
// The OIML R 76-2 form prints two sub-columns per quantity, headed with the
// glyphs "↓" and "↑" (increasing load, then decreasing load). This app's API
// names directions semantically instead ("up" = increasing, "down" =
// decreasing). So: the form's "↓" sub-column is the increasing-load pass,
// i.e. API direction "up"; the form's "↑" sub-column is the decreasing-load
// pass, i.e. API direction "down". The glyph-to-API mapping is deliberately
// crossed like this and must stay exactly as specified.
//
// Its own module (not exported from WeighingFormTable.jsx) specifically so
// GuidedEntryPanel.jsx can import it too without the two components
// importing each other.
export const FORM_COLUMNS = [
  { glyph: "↓", apiDirection: "up" },
  { glyph: "↑", apiDirection: "down" },
];
