import sys
import argparse
import scipy.io
import numpy as np
import matplotlib.pyplot as plt
from fuzzy_match_word import viterbi_align


class Alignment():


	def __init__(self, label, recog_file_path, trans_file_path, output_stm_path, noise_itv):
		self.label = label
		self.recog_file_path = recog_file_path
		self.trans_file_path = trans_file_path
		self.output_stm_path = output_stm_path
		self.noise_itv = noise_itv  # [[t1, t2], [t3]]


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
				if time1 <= t and t <= time2:
					return True
			else:
				end_time = ts[0]
				if t >= end_time:
					return True
		return False


	def _process_recog(self):
		"""
		Process the recognition .ctm file
		:param: 
		:return: a recog_list with format [word, global_time, time_inv]
		"""
		recog_list = list()
		self.fake_start_offset = -1
		self.fake_end_offset = -1
		# with open(self.recog_file_path, 'r', encoding='utf-8') as int_f:
		with open(self.recog_file_path, 'r') as int_f:
			f = iter(int_f)
			for line in f:
				part = line.split()
				if not (float(part[3]) == 0 or self._none_word(part[4]) == True):
					time_global = float(part[2])
					if self.fake_start_offset == -1:
						self.fake_start_offset = time_global
					self.fake_end_offset = time_global
					# only ignore the time stamps before and start offset and the end offset			
					if len(self.noise_itv) >= 2 and (time_global < self.noise_itv[0][1] or time_global > self.noise_itv[-1][0]):
						continue
					recog_list.append([part[4], time_global, float(part[3])]) # [word, time_global, time_inv]
		return recog_list


	def _process_trans(self):
		"""
		Process the transcription TXT file
		:param: 
		:return: a word_list with format [word, 0, 0]
		"""
		t_word = list()
		# with open(self.trans_file_path, 'r', encoding='utf-8') as in_f:
		with open(self.trans_file_path, 'r') as in_f:
			f = iter(in_f)
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
		return t_word


	def process_align(self):
		stm_t_dict = self._process_recog()
		trans_t_dict = self._process_trans()
		align_obj = viterbi_align(stm_t_dict, trans_t_dict, self.label, True)
		self.trans_t_dict = align_obj.viterbi(0, len(stm_t_dict)-1, 0, len(trans_t_dict)-1)


	def post_process(self):
		"""
		fill the deletion with linear interpolation
		:param: None
		:return: None
		"""
		i_s = 0
		i_e = 0
		if self.trans_t_dict[0][1] == 0:
			if len(self.noise_itv) == 0:
				self.trans_t_dict[0][1] = self.fake_start_offset
			else:
				self.trans_t_dict[0][1] = self.noise_itv[0][1]  # start_offset
			self.trans_t_dict[0][2] = 0.1
		if self.trans_t_dict[len(self.trans_t_dict)-1][1] == 0:
			if len(self.noise_itv) == 0:
				self.trans_t_dict[len(self.trans_t_dict)-1][1] = self.fake_end_offset
			else:
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
				"""
				for ts in self.noise_itv:
					if len(ts) == 2:						
						time1 = ts[0]
						time2 = ts[1]
						if s_time < time1 and time2 < e_time:
							e_time = min(e_time, time1)
					else:
						time0 = ts[0]
						if s_time < time0 and time0 < e_time:
							e_time = min(e_time, time0)
				"""
				char_len = 0
				for i in range(i_s, i_e):
					char_len += len(self.trans_t_dict[i][0])
				# ratio = float(self.trans_t_dict[i_e][1]-self.trans_t_dict[i_s][1]) / float(char_len)
				ratio = float(e_time - s_time) / float(char_len)
				char_len = 0
				# s_time = self.trans_t_dict[i_s][1]
				for i in range(i_s+1, i_e):
					char_len += len(self.trans_t_dict[i-1][0])
					self.trans_t_dict[i][1] = s_time + char_len * ratio
					self.trans_t_dict[i][2] = len(self.trans_t_dict[i][0]) * ratio
			i_s = i_e


	def output_align_sentence(self, hist=False):

		wps = list()
		# with open(self.trans_file_path, 'r', encoding='utf-8') as input_f, \
		# 	 open(self.output_stm_path, 'w', encoding='utf-8') as output_f_stm:
		with open(self.trans_file_path, 'r') as input_f, open(self.output_stm_path, 'w') as output_f_stm:

			f = iter(input_f)
			idx = 0
			for line in f:
				word = line.lower().split()
				if len(word) == 0 or len(word) == 1:
					continue
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
					# calculate align words per seconds
					ratio = len(word_idx) / float(end_time - start_time)
					wps.append(ratio)
					# ignore all the sentence which include a noise interval
					contain_noise = False
					for ts in self.noise_itv:
						if len(ts) == 2:
							time1 = ts[0]
							time2 = ts[1]
							if (start_time < time1 and time1 < end_time) or \
							   (start_time < time2 and time2 < end_time):
								contain_noise = True
								break
					if not contain_noise:
						output_f_stm.write('%s 1 %d %.3f %.3f <none> %s\n' % (self.label, label_tag, start_time, end_time, "".join(line_output)))

		wps = sorted(wps)
		# plt.hist(wps)
		# print(wps)
		# plt.savefig("./output/"+self.label+".png")
		scipy.io.savemat("./output/"+self.label+"wps.mat", mdict={'wps':wps})


def get_noise_itv(noise_file_path, conf_level):
	conf = scipy.io.loadmat(noise_file_path)
	conf = conf["conf"]
	frames = int(conf.shape[0] / 10)
	conf = conf[:frames*10,1]
	conf = np.reshape(conf, (-1,10))
	conf_s = np.mean(conf, axis=1)
	seconds = int(conf_s.shape[0] / 5)
	conf_5s = np.mean(np.reshape(conf_s[:seconds*5], (-1,5)), axis=1)

	conf_s = conf_s.tolist()
	conf_5s = conf_5s.tolist()
	inv = list()
	for i in range(len(conf_5s)):
		if conf_5s[i] < conf_level:
			inv.append(i)
	
	inv_5 = list()
	if len(inv) != 0:
		idx_s = inv[0]
		idx_e = inv[0]
		for i in range(1, len(inv)):
			if inv[i] - idx_e == 1:
				idx_e = inv[i]
				continue
			else:
				inv_5.append([idx_s, idx_e])
				idx_s = inv[i]
				idx_e = inv[i]

	final_inv = list()
	if len(inv_5) != 0:
		for i in range(len(inv_5)):
			start_time = inv_5[i][0] * 5
			end_time = (inv_5[i][1] + 1) * 5 - 1
			for k in reversed(range(start_time-5, start_time)):
				if k >= 0 and conf_s[k] < conf_level:
					start_time = k
				else:
					break
			for k in range(end_time, end_time + 5):
				if k < len(conf_s) and conf_s[k] < conf_level:
					end_time = k
				else:
					break
			final_inv.append([start_time, end_time])

	# deal with final output
	if len(final_inv) != 0:
		if len(final_inv) == 1:
			final_inv = list()
		else:
			start_time = final_inv[-1][0]
			end_time = final_inv[-1][1]
			final_inv[-1] = [start_time]

	return final_inv


def parse_arguments():
	parser = argparse.ArgumentParser(description='Process alignment argument.')
	parser.add_argument('--recognition-file-path', dest='recog_file_path', type=str)
	parser.add_argument('--transcription-file-path', dest='trans_file_path', type=str)
	parser.add_argument('--label', dest='label', type=str)
	parser.add_argument('--noise-file-path', dest='noise_file_path', type=str)
	parser.add_argument('--output-file-path', dest='output_file_path', type=str)
	return parser.parse_args()


def main(args):
	args = parse_arguments()

	recog_file_path = args.recog_file_path
	trans_file_path = args.trans_file_path
	label = args.label
	noise_file_path = args.noise_file_path
	output_file_path = args.output_file_path

	noise_itv = get_noise_itv(noise_file_path, 0.25)
	align = Alignment(label, recog_file_path, trans_file_path, output_file_path, noise_itv)
	align.process_align()
	align.post_process()
	align.output_align_sentence()


if __name__ == "__main__":
	main(sys.argv)

