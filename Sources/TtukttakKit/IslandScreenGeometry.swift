import Foundation

/// Resting island dimensions, using a physical notch only when the screen has one.
struct IslandScreenGeometry {
    static let fallbackNotchWidth: CGFloat = 184
    private static let noNotchWidth: CGFloat = 80
    private static let noNotchHeight: CGFloat = 24

    let hasNotch: Bool
    let width: CGFloat
    let height: CGFloat

    init(screenWidth: CGFloat, safeAreaTop: CGFloat,
         auxiliaryLeftWidth: CGFloat?, auxiliaryRightWidth: CGFloat?,
         menuBarHeight: CGFloat) {
        hasNotch = safeAreaTop > 0
        if hasNotch {
            if let left = auxiliaryLeftWidth, let right = auxiliaryRightWidth {
                let measuredWidth = screenWidth - left - right
                width = measuredWidth > 0 && measuredWidth < screenWidth
                    ? measuredWidth : Self.fallbackNotchWidth
            } else {
                width = Self.fallbackNotchWidth
            }
            height = safeAreaTop
        } else {
            width = Self.noNotchWidth
            height = min(Self.noNotchHeight, menuBarHeight)
        }
    }
}

/// Shared by the compact view and the greeting's collapse destination.
struct IslandRestingLayout {
    let width: CGFloat
    let height: CGFloat

    /// The pet is a 20-cell drawing; botDiameter / 20 is its cell. Its tallest scenes (error, sleeping:
    /// the club lies in front) use 18 rows, so the cell is the largest that fits 18 rows in the island:
    /// 1.5 pt (30 pt) in a 28-32 pt notch, smaller in a lower bar (PetSprite.cell rounds it to whole pixels).
    var botDiameter: CGFloat { min(30, max(0, (height - 1) / 18 * 20)) }
    /// Body centre (8 rows above it, up to 10 below): those 18 rows stay inside the island,
    /// on a whole point so the cells land on whole pixels.
    var botCenterY: CGFloat { floor(height / 2 - botDiameter / 40) }
    /// The mini grid is 28 pt (two 12 pt rows); its pets fill 8-9 pt of each row, so it needs no
    /// margin of its own. Unscaled wherever it fits: its 0.5 pt cells stay whole pixels.
    var miniGridScale: CGFloat { min(1, max(0, height) / 28) }
    var miniGridCenterX: CGFloat { width - 40 }
}
