import { RecitationResult, WordMatch, WordMatchStatus } from "../../domain/models/RecitationResult";
import { ArabicTextNormalizer } from "./ArabicTextNormalizer";

export class RecitationComparator {
  private normalizer: ArabicTextNormalizer;

  constructor(normalizer?: ArabicTextNormalizer) {
    this.normalizer = normalizer ?? new ArabicTextNormalizer();
  }

  compare(recitedText: string, expectedText: string): RecitationResult {
    const recitedWords = this.normalizer.splitIntoWords(recitedText);
    const expectedWords = this.normalizer.splitIntoWords(expectedText);

    const alignment = this.alignWords(recitedWords, expectedWords);
    const accuracy = this.calculateAccuracy(alignment, expectedWords.length);

    return {
      recitedText,
      expectedText,
      wordMatches: alignment,
      accuracy,
    };
  }

  private alignWords(recited: string[], expected: string[]): WordMatch[] {
    const dp = this.computeEditDistanceMatrix(recited, expected);
    return this.backtrackAlignment(dp, recited, expected);
  }

  private computeEditDistanceMatrix(recited: string[], expected: string[]): number[][] {
    const m = recited.length;
    const n = expected.length;
    const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

    for (let i = 0; i <= m; i++) dp[i][0] = i;
    for (let j = 0; j <= n; j++) dp[0][j] = j;

    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (recited[i - 1] === expected[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1];
        } else {
          dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
        }
      }
    }

    return dp;
  }

  private backtrackAlignment(
    dp: number[][],
    recited: string[],
    expected: string[],
  ): WordMatch[] {
    const matches: WordMatch[] = [];
    let i = recited.length;
    let j = expected.length;

    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && recited[i - 1] === expected[j - 1]) {
        matches.unshift({
          word: expected[j - 1],
          status: "correct",
        });
        i--;
        j--;
      } else if (i > 0 && j > 0 && dp[i][j] === dp[i - 1][j - 1] + 1) {
        matches.unshift({
          word: recited[i - 1],
          status: "incorrect",
          expectedWord: expected[j - 1],
        });
        i--;
        j--;
      } else if (j > 0 && (i === 0 || dp[i][j - 1] <= dp[i - 1][j])) {
        matches.unshift({
          word: expected[j - 1],
          status: "missing",
        });
        j--;
      } else {
        matches.unshift({
          word: recited[i - 1],
          status: "extra",
        });
        i--;
      }
    }

    return matches;
  }

  private calculateAccuracy(matches: WordMatch[], expectedCount: number): number {
    if (expectedCount === 0) return 1;
    const correctCount = matches.filter((m) => m.status === "correct").length;
    return correctCount / expectedCount;
  }
}
