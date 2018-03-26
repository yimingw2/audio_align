####################################################################
# usage:

# python rough_align.py pattern text Px start_offset end_offset
####################################################################

import sys
from fuzzy_match_word import fuzzy_match


class Alignment():


	def __init__(self, label, recog_file_path, trans_file_path, start_offset, end_offset, output_stm_path, output_ctm_path, noise_itv):
		self.label = label
		self.recog_file_path = recog_file_path
		self.trans_file_path = trans_file_path
		self.start_offset = start_offset
		self.end_offset = end_offset
		self.output_stm_path = output_stm_path
		self.output_ctm_path = output_ctm_path
		self.noise_itv = noise_itv # [[t1, t2], [t3]]


	def _none_word(self, s):
		if s[0] == '[' or s[len(s)-1] == ']' or s[0] == '<' or s[len(s)-1] == '>' or s[0] == '(' or s[len(s)-1] == ')':
			return True
		else:
			return False


	def _is_noise(self, t):
		"""
		Find if a time stamp is noise
		:param t: time stamp
		:return: True is t is noise
		"""
		for ts in self.noise_itv:
			if len(ts) == 2:
				time1 = ts[0]
				time2 = ts[1]
				if t >= time1 and t <= time2:
					return True
			else:
				end_time = ts[0]
				if t >= end_time:
					return True

		return False


	def _process_recog(self):
		"""
		Process the recognition CTM file
		:param: 
		:return: 
		"""
		recog_list = list()
		int_f = open(self.recog_file_path, 'r')
		f = iter(int_f)
		for line in f:
			part = line.split()
			if not (float(part[3]) == 0 or self._none_word(part[4]) == True):
				time_global = float(part[2])
				if self._is_noise(time_global):
					continue
				recog_list.append([part[4], time_global, float(part[3])]) # [word, time_global, time_inv]
		int_f.close()

		return recog_list


	def _process_trans(self):
		"""
		Process the transcription TXT file
		:param: 
		:return: 
		"""
		in_f = open(self.trans_file_path, 'r')
		f = iter(in_f)
		t_word = list()
		for line in f:
			word = line.lower().split();
			if len(word) == 0 or len(word) == 1:
				continue
			'''
			if w_0[len(w_0)-1] == '+': # ignore the label starting with #pat+ || #doc+
				continue;
			'''
			for i in range(len(word)):
				if i != 0: # exclude the channel
					w = word[i]
					if w == "<name>":
						continue
					else:
						t_word.append([w, 0, 0])
		in_f.close()

		return t_word


	def process_align(self):
		stm_t_dict = self._process_recog()
		trans_t_dict = self._process_trans()
		self.trans_t_dict = fuzzy_match(stm_t_dict, 0, len(stm_t_dict)-1, trans_t_dict, 0, len(trans_t_dict)-1)


	def post_process(self):
		"""
		fill the deletion with linear interpolation
		:param: None
		:return: None
		"""
		i_s = 0
		i_e = 0
		if self.trans_t_dict[0][1] == 0:
			self.trans_t_dict[0][1] == self.noise_itv[0][1]  # start_offset
			self.trans_t_dict[0][2] == 0.1
		if self.trans_t_dict[len(self.trans_t_dict)-1][1] == 0:
			self.trans_t_dict[len(self.trans_t_dict)-1][1] = self.noise_itv[-1][0]  # end_offset
			self.trans_t_dict[len(self.trans_t_dict)-1][2] = 0.1

		while i_s < len(self.trans_t_dict):
			while i_s < len(self.trans_t_dict) and self.trans_t_dict[i_s][1] != 0:
				i_s += 1
			if i_s == len(self.trans_t_dict):
				i_e = len(self.trans_t_dict)
			if i_s < len(self.trans_t_dict):
				i_s -= 1
				i_e = i_s + 1
				while i_e < len(self.trans_t_dict) and self.trans_t_dict[i_e][1] == 0:
					i_e += 1
				if i_e == len(self.trans_t_dict):
					break

				# incorperate the noise inverval
				s_time = self.trans_t_dict[i_s][1]
				e_time = self.trans_t_dict[i_e][1]
				for ts in self.noise_itv:
					if len(ts) == 2:						
						time1 = ts[0]
						time2 = ts[1]
						if s_time < time1 and e_time > time2:
							e_time = min(e_time, time1)
					else:
						time0 = ts[0]
						if time0 > time1 and time0 < time2:
							e_time = min(e_time, time0)

				char_len = 0
				for i in range(i_s, i_e):
					char_len += len(self.trans_t_dict[i][0])
				#ratio = float(self.trans_t_dict[i_e][1]-self.trans_t_dict[i_s][1]) / float(char_len)
				ratio = float(e_time - s_time) / float(char_len)
				char_len = 0
				s_time = self.trans_t_dict[i_s][1]
				for i in range(i_s+1, i_e):
					char_len += len(self.trans_t_dict[i-1][0])
					self.trans_t_dict[i][1] = s_time + char_len * ratio
					self.trans_t_dict[i][2] = len(self.trans_t_dict[i][0]) * ratio
			i_s = i_e


	def output_align_sentence(self):
		input_f = open(self.trans_file_path, 'r')
		output_f_stm = open(self.output_stm_path, 'w')
		output_f_ctm = open(self.output_ctm_path, 'w')
		f = iter(input_f)
		idx = 0
		for line in f:
			word = line.lower().split()
			label_tag = word[0]
			if label_tag == "#doc#" or label_tag == "#doc+":
				label_tag = 1
			elif label_tag == "#pat#" or label_tag == "#pat+":
				label_tag = 2
			else:
				label_tag = 3

			word = word[1:]
			line_output = list()
			start_time = 0
			end_time = 0
			word_idx = list()
			for i in range(len(word)):
				if word[i] != "<name>":
					word_idx.append(idx)
					line_output.append(word[i])
					line_output.append(" ")
					idx += 1

			# for stm file
			if len(word_idx) != 0:
				start_time = self.trans_t_dict[word_idx[0]][1]
				tmp_e = self.trans_t_dict[word_idx[len(word_idx)-1]][1]+self.trans_t_dict[word_idx[len(word_idx)-1]][2]
				if word_idx[len(word_idx)-1] == len(self.trans_t_dict)-1 or tmp_e < self.trans_t_dict[word_idx[len(word_idx)-1]+1][1]:
					end_time = tmp_e
				else:
					end_time = self.trans_t_dict[word_idx[len(word_idx)-1]+1][1]
				# since for ASR it should have 0.01s to recognize
				if end_time - start_time < 0.01:
					end_time = start_time + 0.01
				output_f_stm.write('%s %d %s %.3f %.3f <none> %s\n' % (self.label, label_tag, self.label, start_time, end_time, "".join(line_output)))

			# for ctm file
			for i in word_idx:
				output_f_ctm.write("%s %d %.3f %.3f %s 1\n" % (self.label, label_tag, self.trans_t_dict[i][1], self.trans_t_dict[i][2], self.trans_t_dict[i][0]))
			if len(word_idx) != 0:
				output_f_ctm.write("%s %d %.3f 0 <#s> 1\n" % (self.label, label_tag, self.trans_t_dict[word_idx[len(word_idx)-1]][1]+self.trans_t_dict[word_idx[len(word_idx)-1]][2]))

		input_f.close()
		output_f_stm.close()
		output_f_ctm.close()

'''
def write_output(stm_t_dict, output_file_name):
	f = open(output_file_name, 'w')
	for i in range(len(stm_t_dict)):
		f.write('%s\t\t%.3f\t%.3f\n' % (trans_t_dict[i][0], trans_t_dict[i][1], trans_t_dict[i][2]))
	f.close()
'''

def main(align):
	align.process_align()
	align.post_process()
	align.output_align_sentence()


if __name__ == "__main__":
	# argv[1]: pattern
	# argv[2]: text
	# argv[3]: Px
	# argv[4]: start offset
	# argv[5]: end offset

	recog_file_path = sys.argv[1]
	trans_file_path = sys.argv[2]
	label = sys.argv[3]
	start_offset = float(sys.argv[4])
	end_offset = float(sys.argv[5])
	output_ctm_path = 'output_'+sys.argv[3]+'/'+sys.argv[3]+'.ctm'
	output_stm_path = 'output_'+sys.argv[3]+'/'+sys.argv[3]+'_align.stm'
	noise_itv = [[0, 185], [1494.5]]

	align = Alignment(label, recog_file_path, trans_file_path, start_offset, end_offset, output_stm_path, output_ctm_path, noise_itv)
	main(align)

