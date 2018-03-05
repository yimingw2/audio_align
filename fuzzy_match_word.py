def edit_distance(string_a, string_b):

    # length of each string
    len_a = len(string_a)
    len_b = len(string_b)

    # dp table
    dp = [[0 for x in range(len_a+1)] for y in range(len_b+1)]

    # initialize first row and first column
    for i in range(len_a+1):
        dp[0][i] = i

    for i in range(len_b+1):
        dp[i][0] = i

    # dp update
    cost = 0.0
    for i in range(1, len_b+1):
        for j in range(1, len_a+1):
            index_a = j-1
            index_b = i-1
            cost = 0.0 if string_a[index_a] == string_b[index_b] else 1.0

            dp[i][j] = min(dp[i-1][j-1]+cost, min(dp[i-1][j]+1, dp[i][j-1]+1))

    return dp[len_b][len_a]

def compute_cost(string_a, string_b):
    # compute character level cost of two strings
    len_a = len(string_a)
    len_b = len(string_b)
    cost_ed = edit_distance(string_a, string_b)
    return float(cost_ed) / float(max(len_a, len_b))

def compute_extra_cost(string_a):
    return float(len(string_a)) / 5.

def fuzzy_match(pattern, idx1_p, idx2_p, text, idx1_t, idx2_t):
    """
    find the best edit distance

    :param string_a: text
    :param string_b: pattern
    :return: matched string part
    """

    # length of each string
    len_a = idx2_t - idx1_t + 1
    len_b = idx2_p - idx1_p + 1

    # dp table
    # its contents is edit distance, dx, dy to the best previous path
    dp = [[(0, -1, -1) for x in range(len_a+1)] for y in range(len_b+1)]

    # initialize first row and first column
    dp[0][0] = [0, 0, 0]
    for i in range(1, len_a+1):
        dp[0][i] = [i, 0, -1]

    for i in range(1, len_b+1):
        dp[i][0] = [i, -1, 0]

    # dp update
    for i in range(1, len_b+1):
        for j in range(1, len_a+1):
            index_a = j-1
            index_b = i-1

            cost = compute_cost(pattern[idx1_p+index_b][0], text[idx1_t+index_a][0].lower())
            cost_p = 1
            cost_t = 1
            
            dx = 0
            dy = 0
            mincost = 0

            if dp[i-1][j][0] < dp[i][j-1][0]:
                dx = -1
                dy = 0
                mincost = dp[i-1][j][0] + cost_p
            else:
                dx = 0
                dy = -1
                mincost = dp[i][j-1][0] + cost_t

            if dp[i-1][j-1][0] + cost < mincost:
                dx = -1
                dy = -1
                mincost = dp[i-1][j-1][0] + cost

            dp[i][j] = [mincost, dx, dy]

    # backward to get the best_start_index
    cx = len_b
    cy = len_a

    while cy != 0:
        dx = dp[cx][cy][1]
        dy = dp[cx][cy][2]

        if dx == 0 and dy == -1: # deal with deletion
            text[idx1_t+cy-1][1] = 0
        else:
            text[idx1_t+cy-1][1] = pattern[idx1_p+cx-1][1]
            text[idx1_t+cy-1][2] = pattern[idx1_p+cx-1][2]

        cx += dx
        cy += dy

    return text
    