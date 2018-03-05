####################################################################
# usage:

# python rough_align.py pattern text Px start_offset end_offset
####################################################################

import sys
from fuzzy_match_local import fuzzy_match

def none_word(s):
	if s[0] == '[' or s[len(s)-1] == ']' or s[0] == '<' or s[len(s)-1] == '>' or s[0] == '(' or s[len(s)-1] == ')':
		return True
	else:
		return False

def prep_stm(pattern_file, output_file):
	int_f = open(pattern_file, 'r')
	out_f = open(output_file, 'w')
	f = iter(int_f)
	for line in f:
		part = line.split()
		if not (float(part[3]) == 0 or none_word(part[4]) == True):
			out_f.write(line)
	out_f.close()

def get_stm_char(output_file, start_offset, end_offset):
	stm_t_dict = list()
	out_f = open(output_file, 'r')
	f = iter(out_f)
	for line in f:
		part = line.split()
		time_global = float(part[2])
		if time_global <= start_offset or time_global >= end_offset:
			continue
		stm_t_dict.append([part[4], time_global, float(part[3])]) # [word, time_global, time_inv]
	out_f.close()
	return stm_t_dict

# deprecated
def get_trans_char_old(text_file):
	input_f = open(text_file, 'r')
	f = iter(input_f)
	trans_t_dict = list()
	for line in f:
		word = line.lower().split()[1:] # label word[0] is the label tag
		for w in word:
			if none_word(w) == False:
				trans_t_dict.append([w, 0, 0])
	input_f.close()
	return trans_t_dict


def get_trans_char(input_file):
	in_f = open(input_file, 'r')
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


def align(stm_t_dict, trans_t_dict):
	trans_t_dict = fuzzy_match(stm_t_dict, 0, len(stm_t_dict)-1, trans_t_dict, 0, len(trans_t_dict)-1)
	return trans_t_dict

def post_process(trans_t_dict, start_offset, end_offset):
	# fill the deletion with linear interpolation
	i_s = 0
	i_e = 0
	if trans_t_dict[0][1] == 0:
		trans_t_dict[0][1] == start_offset
		trans_t_dict[0][2] == 0.1
	if trans_t_dict[len(trans_t_dict)-1][1] == 0:
		trans_t_dict[len(trans_t_dict)-1][1] = end_offset
		trans_t_dict[len(trans_t_dict)-1][2] = 0.1

	while i_s < len(trans_t_dict):
		while i_s < len(trans_t_dict) and trans_t_dict[i_s][1] != 0:
			i_s += 1
		if i_s == len(trans_t_dict):
			i_e = len(trans_t_dict)
		if i_s < len(trans_t_dict):
			i_s -= 1
			i_e = i_s + 1
			while i_e < len(trans_t_dict) and trans_t_dict[i_e][1] == 0:
				i_e += 1
			if i_e == len(trans_t_dict):
				break
			char_len = 0
			for i in range(i_s, i_e):
				char_len += len(trans_t_dict[i][0])
			ratio = float(trans_t_dict[i_e][1]-trans_t_dict[i_s][1]) / float(char_len)
			char_len = 0
			s_time = trans_t_dict[i_s][1]
			for i in range(i_s+1, i_e):
				char_len += len(trans_t_dict[i-1][0])
				trans_t_dict[i][1] = s_time + char_len * ratio
				trans_t_dict[i][2] = len(trans_t_dict[i][0]) * ratio
		i_s = i_e

	return trans_t_dict

def output_align_sentence(trans_t_dict, trans_sent_file, output_file_stm, output_file_ctm, Px):
	input_f = open(trans_sent_file, 'r')
	output_f_stm = open(output_file_stm, 'w')
	output_f_ctm = open(output_file_ctm, 'w')
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
			start_time = trans_t_dict[word_idx[0]][1]
			tmp_e = trans_t_dict[word_idx[len(word_idx)-1]][1]+trans_t_dict[word_idx[len(word_idx)-1]][2]
			if word_idx[len(word_idx)-1] == len(trans_t_dict)-1 or tmp_e < trans_t_dict[word_idx[len(word_idx)-1]+1][1]:
				end_time = tmp_e
			else:
				end_time = trans_t_dict[word_idx[len(word_idx)-1]+1][1]
			# since for ASR it should have 0.01s to recognize
			if end_time - start_time < 0.01:
				end_time = start_time + 0.01
			output_f_stm.write('%s %d %s %.3f %.3f <none> %s\n' % (Px, label_tag, Px, start_time, end_time, "".join(line_output)))

		# for ctm file
		for i in word_idx:
			output_f_ctm.write("%s %d %.3f %.3f %s 1\n" % (Px, label_tag, trans_t_dict[i][1], trans_t_dict[i][2], trans_t_dict[i][0]))
		if len(word_idx) != 0:
			output_f_ctm.write("%s %d %.3f 0 <#s> 1\n" % (Px, label_tag, trans_t_dict[word_idx[len(word_idx)-1]][1]+trans_t_dict[word_idx[len(word_idx)-1]][2]))

	input_f.close()
	output_f_stm.close()
	output_f_ctm.close()

def write_output(stm_t_dict, output_file_name):
	f = open(output_file_name, 'w')
	for i in range(len(stm_t_dict)):
		f.write('%s\t\t%.3f\t%.3f\n' % (trans_t_dict[i][0], trans_t_dict[i][1], trans_t_dict[i][2]))
	f.close()

if __name__ == "__main__":
	# argv[1]: pattern
	# argv[2]: text
	# argv[3]: Px
	# argv[4]: start offset
	# argv[5]: end offset

	# word level
	start_offset = float(sys.argv[4])
	end_offset = float(sys.argv[5])

	prep_stm(sys.argv[1], 'output_'+sys.argv[3]+'/pattern_word')
	stm_t_dict = get_stm_char('output_'+sys.argv[3]+'/pattern_word', start_offset, end_offset)
	trans_t_dict = get_trans_char(sys.argv[2])
	trans_t_dict = align(stm_t_dict, trans_t_dict)
	trans_t_dict = post_process(trans_t_dict, start_offset, end_offset)
	write_output(trans_t_dict, 'output_'+sys.argv[3]+'/align_word')
	output_align_sentence(trans_t_dict, sys.argv[2], 'output_'+sys.argv[3]+'/'+sys.argv[3]+'_align.stm', 
		'output_'+sys.argv[3]+'/'+sys.argv[3]+'_a.ctm', sys.argv[3])
	# word level end

