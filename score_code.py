import pandas as pd
import numpy as np
import collections


class ScoreSA(object):

    def __init__(self, filename, rescore):
        self.filename = filename
        self.rescore = rescore
        self.raw_df = self.build_raw_df()
        self._has_groups = False
        self.scored_df = self.build_scored_df()
        if self._has_groups:
            self.descriptive_df = self.get_descriptive_stats()

    def build_raw_df(self):
        '''

        turns excel file into pandas dataframe
        '''
        df = pd.read_excel(self.filename, index_col=0, header = 0)
        df.columns = (str(column) for column in df.columns)
        df = self.convert_index(df)
        return df

    def build_scored_df(self):
        '''

        scored raw df and adds weight percentage and group to new scored df
        '''
        # builds the scored dataframe
        weight_percentage = self.get_weight_perc(self.raw_df)
        group = self.get_group(self.raw_df)

        # handles rescoring
        if self.rescore == 'full':
            scored = self.score()
        elif self.rescore == 'score_6':
            scored = self.score(rescore6 = True)
        elif self.rescore == 'score_12':
            scored = self.score(rescore12 = True)

        scored = pd.concat([group, weight_percentage, scored], axis=1)
        scored = scored.dropna(thresh = 6, axis = 0)
        return scored

    def get_descriptive_stats(self):
        '''

        gets descriptive stats from scored df
        '''
        grouped = self.scored_df.groupby('group').describe()
        grouped = self.stdev_2_stderror(grouped)
        return grouped

    #function to score spontaneous alternation
    def score(self, start = 1, rescore = 76, rescore6 = False, rescore12 = False):
        start = str(start)
        rescore = str(rescore)

        #build dataframe to hold rescored values
        infoframe = pd.DataFrame(index = self.raw_df.index,
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
        for index in self.raw_df.index:
            if rescore6:
                rescore = self.raw_df['6min_arm'].ix[index]
                try:
                    rescore = str(int(rescore))
                except:
                    rescore = None
            if rescore12:
                rescore = self.raw_df['12min_arm'].ix[index]
                try:
                    rescore = str(int(rescore))
                except:
                    rescore = None

            if rescore:
                drop = self.raw_df.loc[index, start:rescore].dropna(how='all')

            if len(drop) > 4:
                alts = 0
                possible_alts = len(drop) - 3
                pers = 0
                repeat = 0
                arm_dict = {1:0, 2:0, 3:0, 4:0}
                for n in xrange(0, len(drop)):
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
                                alt_list = drop.iloc[n-3:n].values
                                #alt_list = [drop.iloc[n], drop.iloc[n-1], drop.iloc[n-2], drop.iloc[n-3]]
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


    def convert_index(self, df):
        '''
        input: dataframe
        output: dataframe

        changes index values to strings
        '''
        new_ix = [str(i) for i in df.index]
        df.index = new_ix
        return df

    def get_weight_perc(self, df):
        '''
        input: df
        output: Series

        calculates weight percentages based on pre and post weights if in
        dataframe. Otherwise returns empty strings
        '''
        if False in df['pre_weight'].isnull().values and \
           False in df['post_weight'].isnull().values:
            weight_percentage = df['post_weight'] / df['pre_weight']
        else:
            weight_percentage = pd.Series(['' for ix in df.index],
                                          index = df.index)
        weight_percentage.name = 'weight_percentage'
        return weight_percentage

    def get_group(self, df):
        if False in df['group'].isnull().values:
            group = df['group']
            group = group.replace(np.nan, 'not in group')
            self._has_groups = True
        else:
            group = pd.Series(['' for ix in df.index], index = df.index)
            self._has_groups = False
        group.name = 'group'
        return group

    def stdev_2_stderror(self, describe_df):
        dt = describe_df.T.copy()
        for x in dt.columns.levels[0]:
            count = dt[x]['count'][0]
            dt[x, 'std'] = dt[x]['std'].div(np.sqrt(count))

        new_levels = [name if name != 'std' else 'sterr' for name in dt.columns.levels[1]]
        dt.columns.set_levels(new_levels, level=1, inplace = True)
        return dt.T
