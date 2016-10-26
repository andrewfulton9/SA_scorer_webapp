import pandas as pd
import collections


#function to score spontaneous alternation
def sa(df, start = 1, rescore = 76, rescore6 = False, rescore12 = False, rescore18=False):
    '''
    input: df = dataframe with raw spontaneous alt data
           start = arm to start scoring from
           rescore = arm to stop scoring at
           rescore6 = stop scoring at 6 min mark
           rescore12 = stop scoring at 12 min mark
           rescore18 = stop scoring at 18 min mark
    output: a dataframe with the scored data

    function to score a dataframe with raw spontaneous alternation data
    '''
    df.columns = (str(column) for column in df.columns)
    start = str(start)
    rescore = str(rescore)

    #build dataframe to hold rescored values
    infoframe = pd.DataFrame(index = df.index,
                             columns = ['alternations',
                                        'arm entries',
                                        '% alternation',
                                        '% perseverative errors',
                                        '% repeat entries',
                                        '% 1 entries',
                                        '% 2 entries',
                                        '% 3 entries',
                                        '% 4 entries',
                                        'arm entry inequality'])

    #score SA raw data from excel file and place in infoframe
    for index in df.index:
        if rescore6:
            rescore = df['6min_arm'].ix[index]
            try:
                rescore = str(int(rescore))
            except:
                rescore = None
        if rescore12:
            rescore = df['12min_arm'].ix[index]
            try:
                rescore = str(int(rescore))
            except:
                rescore = None

        if rescore:
            drop = df.loc[:, start:rescore].ix[index].dropna(how='all')
        if len(drop) > 4:
            alts = 0
            possible_alts = len(drop) - 3
            pers = 0
            repeat = 0
            arm_dict = {1:0, 2:0, 3:0, 4:0}
            for n in range(0, len(drop)):
                if drop.iloc[n] not in [1, 2, 3, 4]:
                    raise NameError('invalid arm entry input for subject %s on choice #%s: %s'
                                     % (index, n, drop.iloc[n]))
                arm_dict[drop.iloc[n]] += 1
                if n >= 2:
                    if drop.iloc[n] == drop.iloc[n-1]:
                        repeat += 1
                    if n >= 3:
                        if drop.iloc[n] == drop.iloc[n-2]:
                            pers +=1
                        if n >= 4:
                            alt_list = [drop.iloc[n], drop.iloc[n-1], drop.iloc[n-2], drop.iloc[n-3]]
                            alt_count = collections.Counter(alt_list).values()
                            if True not in map(lambda x: x > 1, alt_count):
                                alts += 1
            per_entry_diff = sum([abs(float(x)/len(drop) - .25)
                                  for x in arm_dict.values()])
            infoframe['alternations'][index] = int(alts)
            infoframe['arm entries'][index] = len(drop)
            infoframe['% alternation'][index] = float(alts)/possible_alts * 100
            infoframe['% perseverative errors'][index] = float(pers)/(len(drop) - 2) * 100
            infoframe['% repeat entries'][index] = float(repeat)/(len(drop) - 1) * 100
            infoframe['% 1 entries'][index] = float(arm_dict[1]) / len(drop) * 100
            infoframe['% 2 entries'][index] = float(arm_dict[2]) / len(drop) * 100
            infoframe['% 3 entries'][index] = float(arm_dict[3]) / len(drop) * 100
            infoframe['% 4 entries'][index] = float(arm_dict[4]) / len(drop) * 100
            infoframe['arm entry inequality'][index] = per_entry_diff / 4 * 100

    return infoframe.astype(float)
